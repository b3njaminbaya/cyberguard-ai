def test_incidents_requires_auth(client):
    assert client.get("/incidents").status_code == 401


def test_create_and_list_incident(authed_client):
    resp = authed_client.post(
        "/incidents",
        json={"title": "Suspicious login", "description": "Multiple failed attempts", "severity": "high"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "open"
    assert body["created_by_email"] == "user@test.local"
    assert body["notes"] == []

    listed = authed_client.get("/incidents").json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_create_incident_linked_to_unknown_threat_404s(authed_client):
    resp = authed_client.post(
        "/incidents",
        json={"title": "x", "severity": "low", "threat_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 404


def test_update_incident_status_and_assignee(authed_client):
    incident = authed_client.post("/incidents", json={"title": "x", "severity": "medium"}).json()
    resp = authed_client.patch(
        f"/incidents/{incident['id']}",
        json={"status": "investigating", "assignee_email": "analyst@test.local"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "investigating"
    assert body["assignee_email"] == "analyst@test.local"


def test_update_unknown_incident_404s(authed_client):
    resp = authed_client.patch("/incidents/00000000-0000-0000-0000-000000000000", json={"status": "closed"})
    assert resp.status_code == 404


def test_add_note_appends_and_returns_incident(authed_client):
    incident = authed_client.post("/incidents", json={"title": "x", "severity": "low"}).json()
    resp = authed_client.post(f"/incidents/{incident['id']}/notes", json={"content": "Looking into it"})
    assert resp.status_code == 200
    notes = resp.json()["notes"]
    assert len(notes) == 1
    assert notes[0]["content"] == "Looking into it"
    assert notes[0]["author_email"] == "user@test.local"


def test_get_single_incident(authed_client):
    incident = authed_client.post("/incidents", json={"title": "x", "severity": "low"}).json()
    resp = authed_client.get(f"/incidents/{incident['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == incident["id"]


def test_get_unknown_incident_404s(authed_client):
    assert authed_client.get("/incidents/00000000-0000-0000-0000-000000000000").status_code == 404
