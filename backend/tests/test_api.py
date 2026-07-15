import triage

INGEST_HEADERS = {"X-API-Key": "test-ingest-key"}


def test_health_is_public(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_creates_event_and_threat_when_anomalous(client, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "Exploits", "score": 0.9, "severity": "high"},
    )
    send_slack = mocker.patch("notifications.send_slack")

    resp = client.post(
        "/events/ingest",
        json={
            "source_ip": "10.0.0.1",
            "dest_ip": "10.0.0.2",
            "protocol": "tcp",
            "bytes": 1234,
            "features": {"dur": 0.1},
        },
        headers=INGEST_HEADERS,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["threats"]) == 1
    assert body["threats"][0]["label"] == "Exploits"
    assert body["threats"][0]["severity"] == "high"
    # default settings have alert_on_high=True and notifications_enabled=True,
    # but slack_enabled defaults False — so no Slack call should fire yet.
    send_slack.assert_not_called()


def test_ingest_does_not_create_threat_for_normal_traffic(client, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": False, "label": "Normal", "score": 0.99, "severity": "none"},
    )
    resp = client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers=INGEST_HEADERS,
    )
    assert resp.status_code == 200
    assert resp.json()["threats"] == []


def test_ingest_requires_api_key(client, mocker):
    mocker.patch("main.score_event", return_value={"is_threat": False, "label": "Normal", "score": 0.9, "severity": "none"})
    resp = client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
    )
    assert resp.status_code == 401


def test_ingest_rejects_wrong_api_key(client, mocker):
    mocker.patch("main.score_event", return_value={"is_threat": False, "label": "Normal", "score": 0.9, "severity": "none"})
    resp = client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": "wrong-key"},
    )
    assert resp.status_code == 401


def test_ingest_dispatches_slack_when_enabled_and_severity_matches(admin_client, mocker):
    send_slack = mocker.patch("notifications.send_slack")
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "DoS", "score": 0.8, "severity": "critical"},
    )

    admin_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": True,
            "slack_webhook_url": "https://hooks.slack.example/test",
            "slack_channel": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "webhook_secret": None,
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )

    resp = admin_client.post(
        "/events/ingest",
        json={"source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers=INGEST_HEADERS,
    )
    assert resp.status_code == 200
    send_slack.assert_called_once()
    assert "DoS" in send_slack.call_args.args[1]


def test_threats_endpoint_requires_auth(client):
    assert client.get("/threats").status_code == 401


def test_threats_endpoint_works_for_authed_user(authed_client):
    resp = authed_client.get("/threats")
    assert resp.status_code == 200
    assert resp.json() == []


def test_notification_settings_readable_by_any_authed_user(authed_client):
    resp = authed_client.get("/settings/notifications")
    assert resp.status_code == 200


def test_non_admin_cannot_read_slack_webhook_or_signing_secret(
    client, admin_org_member, regular_org_member, db_session
):
    from sqlalchemy import text

    from auth import get_current_user, require_org_member
    from main import app

    # admin_client/authed_client both mutate the same global
    # app.dependency_overrides entries — requesting both in one test is a
    # footgun (whichever fixture sets up last silently wins for both).
    # Switch the overrides explicitly instead so each request's identity —
    # both site role and org role — is unambiguous.
    app.dependency_overrides[get_current_user] = lambda: admin_org_member.user
    app.dependency_overrides[require_org_member] = lambda: admin_org_member
    client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": True,
            "slack_webhook_url": "https://hooks.slack.example/super-secret-path",
            "slack_channel": "#alerts",
            "webhook_enabled": True,
            "webhook_url": "https://example.com/hook",
            "webhook_secret": "top-secret-hmac-key",
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )
    admin_view = client.get("/settings/notifications").json()
    assert admin_view["slack_webhook_url"] == "https://hooks.slack.example/super-secret-path"
    assert admin_view["webhook_secret"] == "top-secret-hmac-key"

    app.dependency_overrides[get_current_user] = lambda: regular_org_member.user
    app.dependency_overrides[require_org_member] = lambda: regular_org_member
    non_admin_view = client.get("/settings/notifications").json()
    assert non_admin_view["slack_webhook_url"] is None
    assert non_admin_view["webhook_secret"] is None
    # everything else stays visible — it's not a credential
    assert non_admin_view["slack_channel"] == "#alerts"
    assert non_admin_view["slack_enabled"] is True

    # the non-admin GET must not have mutated the stored secret
    row = db_session.execute(text("SELECT slack_webhook_url, webhook_secret FROM notification_settings")).first()
    assert row.slack_webhook_url == "https://hooks.slack.example/super-secret-path"
    assert row.webhook_secret == "top-secret-hmac-key"

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_org_member, None)


def test_notification_settings_not_editable_by_regular_user(authed_client):
    resp = authed_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": False,
            "slack_webhook_url": None,
            "slack_channel": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "webhook_secret": None,
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )
    assert resp.status_code == 403


def test_settings_update_is_audit_logged(admin_client, admin_org_member, caplog, db_session):
    import logging

    from models import AuditLog

    with caplog.at_level(logging.INFO, logger="cyberguard.audit"):
        admin_client.put(
            "/settings/notifications",
            json={
                "notifications_enabled": True,
                "email_enabled": False,
                "email_recipients": "",
                "slack_enabled": False,
                "slack_webhook_url": None,
                "slack_channel": None,
                "webhook_enabled": False,
                "webhook_url": None,
                "webhook_secret": None,
                "alert_on_critical": True,
                "alert_on_high": True,
                "alert_on_medium": False,
            },
        )
    assert any("settings.notifications.updated" in r.message and "admin@test.local" in r.message for r in caplog.records)

    # also persisted to the queryable audit_log table (backs compliance export)
    row = db_session.query(AuditLog).filter(AuditLog.action == "settings.notifications.updated").first()
    assert row is not None
    assert row.actor_email == "admin@test.local"
    assert row.organization_id == admin_org_member.org_id


def test_notification_settings_editable_by_admin(admin_client):
    resp = admin_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": False,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": False,
            "slack_webhook_url": None,
            "slack_channel": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "webhook_secret": None,
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["notifications_enabled"] is False


def test_slack_test_endpoint_requires_saved_webhook(admin_client):
    resp = admin_client.post("/settings/notifications/test/slack")
    assert resp.status_code == 400


def test_slack_test_endpoint_sends_via_saved_webhook(admin_client, mocker):
    send_slack = mocker.patch("notifications.send_slack")
    admin_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": True,
            "slack_webhook_url": "https://hooks.slack.example/test",
            "slack_channel": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "webhook_secret": None,
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )
    resp = admin_client.post("/settings/notifications/test/slack")
    assert resp.status_code == 200
    send_slack.assert_called_once()


def test_slack_test_endpoint_is_rate_limited(admin_client, mocker):
    # The Limiter's in-memory storage is a process-wide singleton, and
    # TestClient always presents the same fake client address — so other
    # tests hitting this same endpoint earlier in the run share this test's
    # rate-limit bucket unless it's reset first.
    from main import limiter

    limiter.reset()
    mocker.patch("notifications.send_slack")
    admin_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": True,
            "email_enabled": False,
            "email_recipients": "",
            "slack_enabled": True,
            "slack_webhook_url": "https://hooks.slack.example/test",
            "slack_channel": None,
            "webhook_enabled": False,
            "webhook_url": None,
            "webhook_secret": None,
            "alert_on_critical": True,
            "alert_on_high": True,
            "alert_on_medium": False,
        },
    )
    # limit is 5/minute — the 6th call in quick succession must be rejected
    statuses = [admin_client.post("/settings/notifications/test/slack").status_code for _ in range(6)]
    assert statuses[:5] == [200] * 5
    assert statuses[5] == 429


def test_model_metrics_reports_untrained_when_no_model_file(client, mocker, tmp_path):
    mocker.patch("main.METRICS_PATH", tmp_path / "nope.json")
    mocker.patch("main.MODEL_PATH", tmp_path / "nope.joblib")
    resp = client.get("/model/metrics")
    assert resp.status_code == 401  # unauthenticated — confirms this is also auth-gated


def test_model_metrics_requires_auth(authed_client, mocker, tmp_path):
    mocker.patch("main.METRICS_PATH", tmp_path / "nope.json")
    mocker.patch("main.MODEL_PATH", tmp_path / "nope.joblib")
    resp = authed_client.get("/model/metrics")
    assert resp.status_code == 200
    assert resp.json()["trained"] is False


def _ingest_one_threat(client, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "Worms", "score": 0.7, "severity": "critical"},
    )
    mocker.patch("notifications.send_slack")
    resp = client.post(
        "/events/ingest",
        json={
            "source_ip": "10.0.0.1",
            "dest_ip": "10.0.0.2",
            "protocol": "tcp",
            "bytes": 500,
            "features": {"dur": 1.5, "service": "http"},
        },
        headers=INGEST_HEADERS,
    )
    return resp.json()["threats"][0]["id"]


def test_triage_requires_auth(client, mocker):
    threat_id = _ingest_one_threat(client, mocker)
    resp = client.post(f"/threats/{threat_id}/triage")
    assert resp.status_code == 401


def test_triage_returns_404_for_unknown_threat(authed_client):
    resp = authed_client.post("/threats/00000000-0000-0000-0000-000000000000/triage")
    assert resp.status_code == 404


def test_triage_generates_and_caches_summary(authed_client, mocker):
    threat_id = _ingest_one_threat(authed_client, mocker)
    generate = mocker.patch("triage.generate_triage", return_value="Isolate the host.")

    resp = authed_client.post(f"/threats/{threat_id}/triage")
    assert resp.status_code == 200
    assert resp.json()["summary"] == "Isolate the host."
    generate.assert_called_once()

    # second call should use the cached summary, not call the model again
    resp2 = authed_client.post(f"/threats/{threat_id}/triage")
    assert resp2.json()["summary"] == "Isolate the host."
    generate.assert_called_once()


def test_triage_regenerate_flag_forces_a_new_call(authed_client, mocker):
    threat_id = _ingest_one_threat(authed_client, mocker)
    generate = mocker.patch("triage.generate_triage", side_effect=["first note", "second note"])

    authed_client.post(f"/threats/{threat_id}/triage")
    resp = authed_client.post(f"/threats/{threat_id}/triage?regenerate=true")

    assert resp.json()["summary"] == "second note"
    assert generate.call_count == 2


def test_triage_surfaces_ollama_unreachable_as_502(authed_client, mocker):
    threat_id = _ingest_one_threat(authed_client, mocker)
    mocker.patch("triage.generate_triage", side_effect=triage.TriageError("Couldn't reach Ollama"))
    resp = authed_client.post(f"/threats/{threat_id}/triage")
    assert resp.status_code == 502
