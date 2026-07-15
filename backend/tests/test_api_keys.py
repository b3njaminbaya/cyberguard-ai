import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from models import ApiKey


@pytest.fixture
def keypair():
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()


def test_list_api_keys_requires_org_membership(client):
    assert client.get("/api-keys").status_code == 401


def test_regular_member_cannot_create_api_key(authed_client):
    resp = authed_client.post("/api-keys", json={"name": "CI pipeline"})
    assert resp.status_code == 403


def test_org_owner_can_create_api_key(admin_client):
    resp = admin_client.post("/api-keys", json={"name": "CI pipeline"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "CI pipeline"
    assert body["secret"].startswith("cgai_")
    assert body["key_prefix"] == body["secret"][:12]
    assert body["revoked"] is False


def test_created_key_is_hashed_not_stored_raw(admin_client, db_session):
    resp = admin_client.post("/api-keys", json={"name": "CI pipeline"})
    secret = resp.json()["secret"]

    row = db_session.query(ApiKey).filter(ApiKey.name == "CI pipeline").first()
    assert row is not None
    assert row.key_hash != secret
    assert secret not in row.key_hash


def test_list_api_keys_never_returns_the_secret(admin_client):
    admin_client.post("/api-keys", json={"name": "CI pipeline"})
    resp = admin_client.get("/api-keys")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert "secret" not in body[0]


def test_real_api_key_authenticates_ingest_and_resolves_org(admin_client, admin_org_member, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "Exploits", "score": 0.9, "severity": "high"},
    )
    mocker.patch("notifications.send_slack")

    secret = admin_client.post("/api-keys", json={"name": "prod ingest"}).json()["secret"]

    resp = admin_client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": secret},
    )
    assert resp.status_code == 200
    # ingested under the key's own org (admin_org_member's org), not the
    # legacy default org the shared INGEST_API_KEY resolves to
    resp2 = admin_client.get("/threats")
    assert len(resp2.json()) == 1


def test_revoked_api_key_is_rejected(admin_client, mocker):
    mocker.patch("main.score_event", return_value={"is_threat": False, "label": "Normal", "score": 0.9, "severity": "none"})

    created = admin_client.post("/api-keys", json={"name": "temp key"}).json()
    secret, key_id = created["secret"], created["id"]

    revoke_resp = admin_client.delete(f"/api-keys/{key_id}")
    assert revoke_resp.status_code == 200

    resp = admin_client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": secret},
    )
    assert resp.status_code == 401


def test_unknown_api_key_is_rejected(client, mocker):
    mocker.patch("main.score_event", return_value={"is_threat": False, "label": "Normal", "score": 0.9, "severity": "none"})
    resp = client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": "cgai_totally-made-up"},
    )
    assert resp.status_code == 401


def test_revoke_unknown_key_404s(admin_client):
    resp = admin_client.delete("/api-keys/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_org_a_key_cannot_be_revoked_by_org_b(client, mocker, keypair, db_session):
    from sqlalchemy import text

    from tests.test_auth import make_token, use_test_key

    org_a, org_b = "00000000-0000-0000-0000-0000000000c1", "00000000-0000-0000-0000-0000000000c2"
    user_a, user_b = "00000000-0000-0000-0000-0000000000ca", "00000000-0000-0000-0000-0000000000cb"
    for org_id, slug in [(org_a, "key-org-a"), (org_b, "key-org-b")]:
        db_session.execute(text('INSERT INTO neon_auth.organization (id, name, slug) VALUES (:id, :n, :s)'), {"id": org_id, "n": slug, "s": slug})
    for user_id, org_id, email in [(user_a, org_a, "a@key-test.local"), (user_b, org_b, "b@key-test.local")]:
        db_session.execute(text('INSERT INTO neon_auth."user" (id, email, role) VALUES (:id, :email, :role)'), {"id": user_id, "email": email, "role": "user"})
        db_session.execute(
            text('INSERT INTO neon_auth.member (id, "organizationId", "userId", role) VALUES (gen_random_uuid(), :o, :u, :r)'),
            {"o": org_id, "u": user_id, "r": "owner"},
        )
    db_session.commit()

    private_key, public_key = keypair
    use_test_key(mocker, public_key)
    token_a = make_token(private_key, sub=user_a)
    token_b = make_token(private_key, sub=user_b)

    key_id = client.post(
        "/api-keys", json={"name": "org-a-key"},
        headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a},
    ).json()["id"]

    resp = client.delete(f"/api-keys/{key_id}", headers={"Authorization": f"Bearer {token_b}", "X-Organization-Id": org_b})
    assert resp.status_code == 404  # not leaked as 403 — org B shouldn't even know it exists

    # confirmed still usable by org A
    still_there = client.get("/api-keys", headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": org_a}).json()
    assert len(still_there) == 1
    assert still_there[0]["revoked"] is False
