import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

import auth

KID = "test-key-1"


@pytest.fixture
def keypair():
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def make_token(private_key, *, sub, exp_delta=3600, iss=None, aud=None):
    now = int(time.time())
    payload = {
        "sub": sub,
        "iat": now,
        "exp": now + exp_delta,
        "iss": iss or auth.AUTH_ISSUER,
        "aud": aud or auth.AUTH_ISSUER,
    }
    return jwt.encode(payload, private_key, algorithm="EdDSA", headers={"kid": KID})


def use_test_key(mocker, public_key):
    mocker.patch("auth._get_signing_key", return_value=SimpleNamespace(key=public_key))


def test_valid_token_reaches_protected_endpoint(client, mocker, keypair, db_session):
    from sqlalchemy import text

    private_key, public_key = keypair
    user_id = "00000000-0000-0000-0000-000000000099"
    db_session.execute(
        text('INSERT INTO neon_auth."user" (id, email, role) VALUES (:id, :email, :role)'),
        {"id": user_id, "email": "verified@test.local", "role": "user"},
    )
    db_session.commit()

    use_test_key(mocker, public_key)
    token = make_token(private_key, sub=user_id)

    # /users/me only needs a valid JWT (get_current_user), not org
    # membership — org-scoped authorization is covered separately in
    # test_organizations.py, and mixing the two here would test both at once.
    resp = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_missing_token_is_rejected(client):
    resp = client.get("/threats")
    assert resp.status_code == 401


def test_garbage_token_is_rejected(client):
    resp = client.get("/threats", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert resp.status_code == 401


def test_expired_token_is_rejected(client, mocker, keypair):
    private_key, public_key = keypair
    use_test_key(mocker, public_key)
    token = make_token(private_key, sub="00000000-0000-0000-0000-000000000099", exp_delta=-60)

    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_wrong_audience_is_rejected(client, mocker, keypair):
    private_key, public_key = keypair
    use_test_key(mocker, public_key)
    token = make_token(private_key, sub="00000000-0000-0000-0000-000000000099", aud="https://not-us.invalid")

    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_valid_signature_but_unknown_user_is_rejected(client, mocker, keypair):
    private_key, public_key = keypair
    use_test_key(mocker, public_key)
    token = make_token(private_key, sub="00000000-0000-0000-0000-0000000000ff")

    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
