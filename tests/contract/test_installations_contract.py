"""Contract: locations, cameras and zones with the pending events of each one."""

from tests.contract.conftest import KEY


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
