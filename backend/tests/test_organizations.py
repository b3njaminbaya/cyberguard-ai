"""Exercises the real require_org_member/require_org_role dependencies (no
dependency_overrides) — real JWTs, real neon_auth.member rows, two distinct
organizations — to prove data is actually isolated between tenants, not
just that the plumbing compiles."""

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import text

from models import Incident, LogEvent, Threat
from tests.test_auth import make_token, use_test_key


@pytest.fixture
def keypair():
    private_key = Ed25519PrivateKey.generate()
    return private_key, private_key.public_key()

ORG_A = "00000000-0000-0000-0000-0000000000a1"
ORG_B = "00000000-0000-0000-0000-0000000000b2"
USER_A = "00000000-0000-0000-0000-0000000000a9"
USER_B = "00000000-0000-0000-0000-0000000000b9"


def _make_org(db_session, org_id, slug):
    db_session.execute(
        text('INSERT INTO neon_auth.organization (id, name, slug) VALUES (:id, :name, :slug)'),
        {"id": org_id, "name": slug, "slug": slug},
    )
    db_session.commit()


def _make_member(db_session, org_id, user_id, email, role="owner"):
    db_session.execute(
        text('INSERT INTO neon_auth."user" (id, email, role) VALUES (:id, :email, :role)'),
        {"id": user_id, "email": email, "role": "user"},
    )
    db_session.execute(
        text(
            'INSERT INTO neon_auth.member (id, "organizationId", "userId", role) '
            'VALUES (gen_random_uuid(), :org_id, :user_id, :role)'
        ),
        {"org_id": org_id, "user_id": user_id, "role": role},
    )
    db_session.commit()


def _two_orgs(db_session):
    """org A and org B each with one distinct member (owner)."""
    _make_org(db_session, ORG_A, "org-a")
    _make_org(db_session, ORG_B, "org-b")
    _make_member(db_session, ORG_A, USER_A, "a@org-a.test", role="owner")
    _make_member(db_session, ORG_B, USER_B, "b@org-b.test", role="owner")


def _token_for(mocker, keypair, user_id):
    private_key, public_key = keypair
    use_test_key(mocker, public_key)
    return make_token(private_key, sub=user_id)


def test_require_org_member_rejects_missing_header(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    token = _token_for(mocker, keypair, USER_A)
    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 400


def test_require_org_member_rejects_non_member(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    token = _token_for(mocker, keypair, USER_A)
    # USER_A is a member of ORG_A only — try to act as ORG_B.
    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}", "X-Organization-Id": ORG_B})
    assert resp.status_code == 403


def test_require_org_member_accepts_real_membership(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    token = _token_for(mocker, keypair, USER_A)
    resp = client.get("/threats", headers={"Authorization": f"Bearer {token}", "X-Organization-Id": ORG_A})
    assert resp.status_code == 200
    assert resp.json() == []


def _seed_event_and_threat(db_session, org_id, label="Exploits"):
    event = LogEvent(organization_id=org_id, source_ip="10.0.0.1", dest_ip="10.0.0.2", protocol="tcp", bytes=1)
    db_session.add(event)
    db_session.flush()
    threat = Threat(organization_id=org_id, event_id=event.id, score=0.9, label=label, severity="high")
    db_session.add(threat)
    db_session.commit()
    db_session.refresh(threat)
    return event, threat


def test_threats_list_is_isolated_between_orgs(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    _seed_event_and_threat(db_session, ORG_A, label="OrgA-Threat")
    _seed_event_and_threat(db_session, ORG_B, label="OrgB-Threat")

    token_a = _token_for(mocker, keypair, USER_A)
    resp = client.get("/threats", headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": ORG_A})
    labels = [t["label"] for t in resp.json()]
    assert labels == ["OrgA-Threat"]


def test_threat_from_other_org_is_not_reachable_by_id(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    _, threat_b = _seed_event_and_threat(db_session, ORG_B, label="OrgB-Threat")

    token_a = _token_for(mocker, keypair, USER_A)
    resp = client.get(
        f"/threats/{threat_b.id}/explain", headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": ORG_A}
    )
    # Not leaked as a 403 (which would confirm existence) — looks identical
    # to "doesn't exist", same as an unknown ID.
    assert resp.status_code == 404


def test_incident_from_other_org_is_not_reachable(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    incident = Incident(organization_id=ORG_B, title="B's incident", severity="high", created_by_email="b@org-b.test")
    db_session.add(incident)
    db_session.commit()
    db_session.refresh(incident)

    token_a = _token_for(mocker, keypair, USER_A)
    resp = client.get(
        f"/incidents/{incident.id}", headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": ORG_A}
    )
    assert resp.status_code == 404


def test_org_member_role_cannot_write_notification_settings(client, mocker, keypair, db_session):
    _make_org(db_session, ORG_A, "org-a")
    _make_member(db_session, ORG_A, USER_A, "member@org-a.test", role="member")
    token = _token_for(mocker, keypair, USER_A)

    resp = client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True, "email_enabled": False, "email_recipients": "",
            "slack_enabled": False, "slack_webhook_url": None, "slack_channel": None,
            "webhook_enabled": False, "webhook_url": None, "webhook_secret": None,
            "alert_on_critical": True, "alert_on_high": True, "alert_on_medium": False,
        },
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": ORG_A},
    )
    assert resp.status_code == 403


def test_org_owner_role_can_write_notification_settings(client, mocker, keypair, db_session):
    _make_org(db_session, ORG_A, "org-a")
    _make_member(db_session, ORG_A, USER_A, "owner@org-a.test", role="owner")
    token = _token_for(mocker, keypair, USER_A)

    resp = client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True, "email_enabled": False, "email_recipients": "",
            "slack_enabled": False, "slack_webhook_url": None, "slack_channel": None,
            "webhook_enabled": False, "webhook_url": None, "webhook_secret": None,
            "alert_on_critical": True, "alert_on_high": True, "alert_on_medium": False,
        },
        headers={"Authorization": f"Bearer {token}", "X-Organization-Id": ORG_A},
    )
    assert resp.status_code == 200


def test_factory_reset_only_wipes_calling_org(client, mocker, keypair, db_session):
    _two_orgs(db_session)
    _seed_event_and_threat(db_session, ORG_A, label="OrgA-Threat")
    _seed_event_and_threat(db_session, ORG_B, label="OrgB-Threat")

    token_a = _token_for(mocker, keypair, USER_A)
    resp = client.post(
        "/system/factory-reset?confirm=RESET",
        headers={"Authorization": f"Bearer {token_a}", "X-Organization-Id": ORG_A},
    )
    assert resp.status_code == 200

    assert db_session.query(Threat).filter(Threat.organization_id == ORG_A).count() == 0
    assert db_session.query(Threat).filter(Threat.organization_id == ORG_B).count() == 1
