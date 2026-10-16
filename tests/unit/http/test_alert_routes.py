import pytest

KEY = {"X-API-Key": "test-key"}


@pytest.fixture
def events(client, clock):
    created = {}
    for name, camera_id, event_type_id in [("ruido", 1, 3), ("caida", 1, 1), ("humo", 2, 4)]:
        response = client.post(
            "/api/eventos",
            json={"camera_id": camera_id, "event_type_id": event_type_id},
            headers=KEY,
        )
        created[name] = response.json()
        clock.advance(1)
    return created


def test_pending_alerts_in_priority_order(client, events):
    response = client.get("/api/alertas/pendientes")
    assert response.status_code == 200
    alerts = response.json()
    assert [a["event"]["id"] for a in alerts] == [
        events["caida"]["id"],
        events["humo"]["id"],
        events["ruido"]["id"],
    ]
    assert alerts[0] == {
        "id_alerta": 2,
        "nivel": "Alto",
        "estado": "Activa",
        "event": events["caida"],
    }
    assert len(client.get("/api/alertas/pendientes", params={"limit": 1}).json()) == 1


@pytest.mark.parametrize("limit", [0, 101])
def test_pending_alerts_limit_is_validated(client, limit):
    assert client.get("/api/alertas/pendientes", params={"limit": limit}).status_code == 422


def test_metrics(client, events):
    assert client.get("/api/metricas").json() == {"total": 3, "pendientes": 3, "alto": 2}
    client.patch(f"/api/eventos/{events['caida']['id']}/revisar")
    assert client.get("/api/metricas").json() == {"total": 3, "pendientes": 2, "alto": 2}
