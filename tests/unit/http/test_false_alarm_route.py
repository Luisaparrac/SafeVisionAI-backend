KEY = {"X-API-Key": "test-key"}


def post(client, **body):
    return client.post("/api/eventos", json=body, headers=KEY).json()


def test_false_alarm_closes_the_event_and_dismisses_its_alert(client, uow):
    created = post(client, camera_id=1, event_type_id=1)
    response = client.patch(f"/api/eventos/{created['id']}/falsa-alarma")
    assert response.status_code == 200
    assert response.json() == created | {"status": "Revisado"}
    assert uow.events.get(created["id"]).status.value == "false_alarm"
    assert [a.status.value for a in uow.alerts.find_by_event(created["id"])] == ["dismissed"]
    assert client.get("/api/alertas/pendientes").json() == []
    assert client.get("/api/metricas").json()["pendientes"] == 0


def test_false_alarm_is_idempotent(client):
    created = post(client, camera_id=1, event_type_id=1)
    first = client.patch(f"/api/eventos/{created['id']}/falsa-alarma")
    again = client.patch(f"/api/eventos/{created['id']}/falsa-alarma")
    assert again.status_code == 200
    assert again.json() == first.json()


def test_resolved_event_keeps_its_review(client):
    created = post(client, camera_id=1, event_type_id=1)
    client.patch(f"/api/eventos/{created['id']}/revisar")
    response = client.patch(f"/api/eventos/{created['id']}/falsa-alarma")
    assert response.status_code == 409
    assert isinstance(response.json()["detail"], str)


def test_unknown_event(client):
    assert client.patch("/api/eventos/999/falsa-alarma").status_code == 404
