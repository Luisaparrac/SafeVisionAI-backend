KEY = {"X-API-Key": "test-key"}


def post(client, **body):
    return client.post("/api/eventos", json=body, headers=KEY).json()


def test_seen_alert_stays_pending_with_its_new_status(client):
    event = post(client, camera_id=1, event_type_id=1)
    [pending] = client.get("/api/alertas/pendientes").json()
    response = client.patch(f"/api/alertas/{pending['id_alerta']}/vista")
    assert response.status_code == 200
    assert response.json() == pending | {"estado": "Vista"}
    assert client.get("/api/alertas/pendientes").json() == [pending | {"estado": "Vista"}]
    assert client.get("/api/metricas").json()["pendientes"] == 1
    assert response.json()["event"] == event


def test_marking_twice_changes_nothing(client):
    post(client, camera_id=1, event_type_id=1)
    first = client.patch("/api/alertas/1/vista")
    again = client.patch("/api/alertas/1/vista")
    assert again.status_code == 200
    assert again.json() == first.json()


def test_closed_alert_cannot_be_marked_as_seen(client):
    event = post(client, camera_id=1, event_type_id=1)
    client.patch(f"/api/eventos/{event['id']}/revisar")
    response = client.patch("/api/alertas/1/vista")
    assert response.status_code == 409


def test_unknown_alert(client):
    response = client.patch("/api/alertas/999/vista")
    assert response.status_code == 404
    assert response.json() == {"detail": "Alerta 999 no existe"}
