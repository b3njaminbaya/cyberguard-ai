def test_general_settings_readable_by_any_authed_user(authed_client):
    resp = authed_client.get("/settings/general")
    assert resp.status_code == 200
    assert resp.json()["org_name"] == "CyberGuard Security"


def test_general_settings_not_editable_by_regular_user(authed_client):
    resp = authed_client.put(
        "/settings/general",
        json={"org_name": "Hacked Inc", "contact_email": "", "timezone": "utc", "log_retention_days": 90},
    )
    assert resp.status_code == 403


def test_admin_can_update_general_settings(admin_client):
    resp = admin_client.put(
        "/settings/general",
        json={"org_name": "New Org", "contact_email": "a@b.com", "timezone": "pst", "log_retention_days": 30},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["org_name"] == "New Org"
    assert body["timezone"] == "pst"


def test_retrain_requires_admin(authed_client):
    assert authed_client.post("/model/retrain").status_code == 403


def test_retrain_returns_metrics_and_reloads_model(admin_client, mocker, tmp_path):
    fake_dataset = tmp_path / "dataset.csv"
    fake_dataset.write_text("id\n1\n")
    mocker.patch("main.TRAIN_DATA_PATH", fake_dataset)
    reload_model = mocker.patch("main.reload_model")
    mocker.patch(
        "main.train_model",
        return_value={
            "accuracy": 0.9,
            "macro avg": {"f1-score": 0.8},
            "weighted avg": {"f1-score": 0.85},
            "Normal": {"precision": 0.9, "recall": 0.9, "f1-score": 0.9, "support": 100},
        },
    )
    resp = admin_client.post("/model/retrain")
    assert resp.status_code == 200
    body = resp.json()
    assert body["accuracy"] == 0.9
    assert body["trained"] is True
    reload_model.assert_called_once()


def test_retrain_503s_when_dataset_missing(admin_client, mocker, tmp_path):
    mocker.patch("main.TRAIN_DATA_PATH", tmp_path / "does-not-exist.csv")
    resp = admin_client.post("/model/retrain")
    assert resp.status_code == 503


def test_system_health_requires_auth(client):
    assert client.get("/system/health").status_code == 401


def test_system_health_reports_real_counts(authed_client, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "DoS", "score": 0.5, "severity": "critical"},
    )
    mocker.patch("notifications.send_slack")
    authed_client.post(
        "/events/ingest",
        json={"source_ip": "1.1.1.1", "dest_ip": "2.2.2.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": "test-ingest-key"},
    )
    resp = authed_client.get("/system/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_events"] == 1
    assert body["total_threats"] == 1
    assert body["database_connected"] is True
    assert body["uptime_seconds"] >= 0


def test_reset_notification_settings_requires_admin(authed_client):
    assert authed_client.post("/settings/notifications/reset").status_code == 403


def test_admin_can_reset_notification_settings(admin_client):
    admin_client.put(
        "/settings/notifications",
        json={
            "notifications_enabled": False, "email_enabled": True, "email_recipients": "a@b.com",
            "slack_enabled": True, "slack_webhook_url": "https://x.example", "slack_channel": "#x",
            "webhook_enabled": True, "webhook_url": "https://y.example", "webhook_secret": "s",
            "alert_on_critical": False, "alert_on_high": False, "alert_on_medium": True,
        },
    )
    resp = admin_client.post("/settings/notifications/reset")
    assert resp.status_code == 200

    settings = admin_client.get("/settings/notifications").json()
    assert settings["notifications_enabled"] is True
    assert settings["slack_enabled"] is False
    assert settings["slack_webhook_url"] is None


def test_factory_reset_requires_admin(authed_client):
    assert authed_client.post("/system/factory-reset?confirm=RESET").status_code == 403


def test_factory_reset_requires_exact_confirmation_string(admin_client):
    resp = admin_client.post("/system/factory-reset?confirm=please")
    assert resp.status_code == 400


def test_factory_reset_wipes_events_and_threats_not_settings(admin_client, mocker):
    mocker.patch("main.score_event", return_value={"is_threat": True, "label": "DoS", "score": 0.5, "severity": "critical"})
    mocker.patch("notifications.send_slack")
    admin_client.post(
        "/events/ingest",
        json={"source_ip": "1.1.1.1", "dest_ip": "2.2.2.2", "protocol": "tcp", "bytes": 1, "features": {}},
        headers={"X-API-Key": "test-ingest-key"},
    )
    admin_client.put(
        "/settings/general",
        json={"org_name": "Keep Me", "contact_email": "", "timezone": "utc", "log_retention_days": 90},
    )

    resp = admin_client.post("/system/factory-reset?confirm=RESET")
    assert resp.status_code == 200

    assert admin_client.get("/threats").json() == []
    # general settings (config, not ingested data) must survive a factory reset
    assert admin_client.get("/settings/general").json()["org_name"] == "Keep Me"
