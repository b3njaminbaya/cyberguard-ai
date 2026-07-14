import hmac
import os
import time
from urllib.parse import urlparse

import jwt
import requests
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db

load_dotenv()

NEON_AUTH_URL = os.environ["NEON_AUTH_URL"]
INGEST_API_KEY = os.environ.get("INGEST_API_KEY")
_AUTH_ORIGIN = urlparse(NEON_AUTH_URL)
AUTH_ISSUER = f"{_AUTH_ORIGIN.scheme}://{_AUTH_ORIGIN.netloc}"
JWKS_URL = f"{NEON_AUTH_URL}/.well-known/jwks.json"

_jwks_cache: dict = {"keys": {}, "fetched_at": 0.0}
JWKS_TTL_SECONDS = 300


def _get_signing_key(kid: str):
    now = time.time()
    if kid not in _jwks_cache["keys"] or now - _jwks_cache["fetched_at"] > JWKS_TTL_SECONDS:
        resp = requests.get(JWKS_URL, timeout=5)
        resp.raise_for_status()
        client = jwt.PyJWKClient(JWKS_URL)
        _jwks_cache["client"] = client
        _jwks_cache["fetched_at"] = now
        _jwks_cache["keys"] = {k["kid"]: True for k in resp.json()["keys"]}

    if kid not in _jwks_cache["keys"]:
        raise HTTPException(status_code=401, detail="Unknown signing key")
    return _jwks_cache["client"].get_signing_key(kid)


class CurrentUser:
    def __init__(self, id: str, email: str, role: str):
        self.id = id
        self.email = email
        self.role = role


def get_current_user(request: Request, db: Session = Depends(get_db)) -> CurrentUser:
    authorization = request.headers.get("authorization", "")
    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]

    try:
        unverified_header = jwt.get_unverified_header(token)
        signing_key = _get_signing_key(unverified_header["kid"])
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["EdDSA"],
            issuer=AUTH_ISSUER,
            audience=AUTH_ISSUER,
        )
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    user_id = payload["sub"]
    row = db.execute(
        text('SELECT email, role, banned FROM neon_auth."user" WHERE id = :id'),
        {"id": user_id},
    ).first()
    if row is None:
        raise HTTPException(status_code=401, detail="User not found")
    if row.banned:
        # Enforced here rather than relying solely on Neon Auth's own ban
        # plugin (unconfirmed whether it's active for this project) — a
        # suspended user's existing, still-valid JWT must stop working
        # against our API regardless of what Neon Auth itself does with it.
        raise HTTPException(status_code=403, detail="This account has been suspended")

    return CurrentUser(id=user_id, email=row.email, role=row.role)


def require_ingest_key(request: Request) -> None:
    if not INGEST_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="INGEST_API_KEY not configured on the backend — ingestion is disabled until it is set.",
        )
    provided = request.headers.get("x-api-key", "")
    if not hmac.compare_digest(provided, INGEST_API_KEY):
        raise HTTPException(status_code=401, detail="Missing or invalid X-API-Key")


def require_role(*roles: str):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
