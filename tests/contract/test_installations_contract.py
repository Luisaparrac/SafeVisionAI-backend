"""Contract: locations, cameras and zones with the pending events of each one."""

from tests.contract.conftest import KEY, post_event


def zone(**changes) -> dict:
    return {
        "zone_id": 1,
        "name": "Escalera",
        "own_pending": 0,
        "pending": 0,
        "max_severity": None,
        "priority": None,
    } | changes


def camera(camera_id: int, name: str, zones: list, **changes) -> dict:
    return {
        "camera_id": camera_id,
        "name": name,
        "status": "active",
        "own_pending": 0,
        "pending": 0,
        "max_severity": None,
        "priority": None,
        "zones": zones,
    } | changes


def test_exact_shape_without_pending_events(client):
    response = client.get("/api/instalaciones")
    assert response.status_code == 200
    assert response.json() == {
        "pending": 0,
        "max_severity": None,
        "priority": None,
        "locations": [
            {
                "location_id": 1,
                "name": "Casa",
                "own_pending": 0,
                "pending": 0,
                "max_severity": None,
                "priority": None,
                "cameras": [camera(2, "Patio", []), camera(1, "Sala", [zone()])],
            }
        ],
    }


def test_the_iot_key_can_read_it(client):
    client.cookies.clear()
    assert client.get("/api/instalaciones", headers=KEY).status_code == 200


def test_requires_a_session(client):
    client.cookies.clear()
    response = client.get("/api/instalaciones")
    assert response.status_code == 401
    assert response.json() == {"detail": "Inicia sesión para continuar"}


def test_pending_events_go_up_to_the_totals(client):
    post_event(client, camera_id=1, event_type="Caída", zone_id=1)
    post_event(client, camera_id=1, event_type="Ruido")
    post_event(client, camera_id=2, event_type="Merodeo")

    body = client.get("/api/instalaciones").json()

    assert (body["pending"], body["max_severity"], body["priority"]) == (3, 4, "Alto")
    assert body["locations"] == [
        {
            "location_id": 1,
            "name": "Casa",
            "own_pending": 0,
            "pending": 3,
            "max_severity": 4,
            "priority": "Alto",
            "cameras": [
                camera(2, "Patio", [], own_pending=1, pending=1, max_severity=2, priority="Medio"),
                camera(
                    1,
                    "Sala",
                    [zone(own_pending=1, pending=1, max_severity=4, priority="Alto")],
                    own_pending=1,
                    pending=2,
                    max_severity=4,
                    priority="Alto",
                ),
            ],
        }
    ]


def test_the_total_is_the_pending_count_of_the_metrics(client):
    post_event(client, camera_id=1, event_type="Caída", zone_id=1)
    closed = post_event(client, camera_id=2, event_type="Humo")
    post_event(client, camera_id=2, event_type="Ruido")
    assert client.patch(f"/api/eventos/{closed['id']}/revisar").status_code == 200

    total = client.get("/api/instalaciones").json()["pending"]

    assert total == client.get("/api/metricas").json()["pendientes"] == 2
