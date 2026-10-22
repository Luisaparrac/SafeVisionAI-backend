from tests.unit.http.conftest import log_in

KEY = {"X-API-Key": "test-key"}


def post(client, camera_id, event_type_id):
    response = client.post(
        "/api/eventos",
        json={"camera_id": camera_id, "event_type_id": event_type_id},
        headers=KEY,
    )
    assert response.status_code == 201


def test_statistics_by_type(client):
    post(client, 1, 1)
    response = client.get("/api/estadisticas/tipos")
    assert response.status_code == 200
    assert response.json()[0] == {
        "event_type_id": 1,
        "name": "Caída",
        "priority": "Alto",
        "total": 1,
    }
    assert [row["total"] for row in response.json()] == [1, 0, 0, 0]


def test_statistics_by_camera_with_dates(client, clock):
    # FakeClock: 2026-10-14 07:00 in Bogotá.
    post(client, 2, 3)
    clock.advance(24 * 3600)
    log_in(client)  # the session of yesterday has expired
    post(client, 1, 3)
    everything = client.get("/api/estadisticas/camaras").json()
    assert everything == [
        {"camera_id": 1, "name": "Sala", "total": 1},
        {"camera_id": 2, "name": "Patio", "total": 1},
    ]
    first_day = client.get(
        "/api/estadisticas/camaras", params={"desde": "2026-10-14", "hasta": "2026-10-14"}
    )
    assert first_day.json() == [
        {"camera_id": 2, "name": "Patio", "total": 1},
        {"camera_id": 1, "name": "Sala", "total": 0},
    ]


def test_statistics_validate_dates(client):
    reversed_range = {"desde": "2026-10-15", "hasta": "2026-10-14"}
    assert client.get("/api/estadisticas/tipos", params=reversed_range).status_code == 422
    assert client.get("/api/estadisticas/camaras", params={"desde": "ayer"}).status_code == 422
