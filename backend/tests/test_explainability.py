import json

import pytest


@pytest.fixture
def fake_explain_file(tmp_path, mocker):
    explain_path = tmp_path / "explainability.json"
    explain_path.write_text(
        json.dumps(
            {
                "feature_importance": {"sbytes": 0.2, "sttl": 0.15, "proto": 0.05},
                "normal_baseline": {
                    "sbytes": {"mean": 1000.0, "std": 500.0},
                    "sttl": {"mean": 60.0, "std": 10.0},
                },
            }
        )
    )
    mocker.patch("detection.predict.EXPLAIN_PATH", explain_path)
    return explain_path


def test_feature_importance_included_in_model_metrics(authed_client, mocker, tmp_path, fake_explain_file):
    fake_metrics = tmp_path / "metrics.json"
    fake_metrics.write_text(json.dumps({"accuracy": 0.8}))
    fake_model = tmp_path / "model.joblib"
    fake_model.write_text("fake")
    mocker.patch("main.METRICS_PATH", fake_metrics)
    mocker.patch("main.MODEL_PATH", fake_model)

    resp = authed_client.get("/model/metrics")
    assert resp.status_code == 200
    body = resp.json()
    assert body["feature_importance"][0]["feature"] == "sbytes"
    assert body["feature_importance"][0]["importance"] == 0.2


def test_feature_importance_empty_list_when_no_explain_file(authed_client, mocker, tmp_path):
    mocker.patch("detection.predict.EXPLAIN_PATH", tmp_path / "missing.json")
    fake_metrics = tmp_path / "metrics.json"
    fake_metrics.write_text(json.dumps({"accuracy": 0.8}))
    fake_model = tmp_path / "model.joblib"
    fake_model.write_text("fake")
    mocker.patch("main.METRICS_PATH", fake_metrics)
    mocker.patch("main.MODEL_PATH", fake_model)

    resp = authed_client.get("/model/metrics")
    assert resp.json()["feature_importance"] == []


def _ingest_worm_event(client, mocker):
    mocker.patch(
        "main.score_event",
        return_value={"is_threat": True, "label": "Worms", "score": 0.6, "severity": "critical"},
    )
    mocker.patch("notifications.send_slack")
    resp = client.post(
        "/events/ingest",
        json={
            "source_ip": "10.0.0.1", "dest_ip": "10.0.0.2", "protocol": "tcp", "bytes": 50000,
            "features": {"sbytes": 50000, "sttl": 90},
        },
        headers={"X-API-Key": "test-ingest-key"},
    )
    return resp.json()["threats"][0]["id"]


def test_explain_requires_auth(client, mocker, fake_explain_file):
    threat_id = _ingest_worm_event(client, mocker)
    assert client.get(f"/threats/{threat_id}/explain").status_code == 401


def test_explain_returns_404_for_unknown_threat(authed_client):
    resp = authed_client.get("/threats/00000000-0000-0000-0000-000000000000/explain")
    assert resp.status_code == 404


def test_explain_computes_real_zscore_against_baseline(authed_client, mocker, fake_explain_file):
    threat_id = _ingest_worm_event(authed_client, mocker)
    resp = authed_client.get(f"/threats/{threat_id}/explain")
    assert resp.status_code == 200
    body = resp.json()
    sbytes_item = next(item for item in body if item["feature"] == "sbytes")
    # (50000 - 1000) / 500 == 98
    assert sbytes_item["z_score"] == pytest.approx(98.0)
    assert sbytes_item["value"] == 50000.0
