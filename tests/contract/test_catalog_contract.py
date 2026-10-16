"""Contract: read-only catalogs and the camera status reported by the IoT module."""

import pytest

from tests.contract.conftest import KEY

pytestmark = pytest.mark.integration


def test_event_types_most_severe_first(client):
    response = client.get("/api/tipos-evento")
    assert response.status_code == 200
    assert response.json() == [
        {
            "event_type_id": 1,
            "name": "Caída",
            "description": None,
            "severity_level": 4,
            "priority": "Alto",
        },
        {
            "event_type_id": 4,
            "name": "Humo",
            "description": None,
            "severity_level": 3,
            "priority": "Alto",
        },
        {
            "event_type_id": 2,
            "name": "Merodeo",
            "description": None,
            "severity_level": 2,
            "priority": "Medio",
        },
        {
            "event_type_id": 3,
            "name": "Ruido",
            "description": None,
            "severity_level": 1,
            "priority": "Bajo",
        },
    ]


def test_locations(client):
    response = client.get("/api/ubicaciones")
    assert response.status_code == 200
    assert response.json() == [{"location_id": 1, "name": "Casa", "description": None}]


def test_cameras(client):
    response = client.get("/api/camaras")
    assert response.status_code == 200
    assert response.json() == [
        {
            "camera_id": 1,
            "name": "Sala",
            "ip_address": "192.0.2.1",
            "status": "active",
            "location_id": 1,
        },
        {
            "camera_id": 2,
            "name": "Patio",
            "ip_address": "192.0.2.2",
            "status": "active",
            "location_id": 1,
        },
    ]


def test_zones(client):
    response = client.get("/api/zonas")
    assert response.status_code == 200
    assert response.json() == [
        {
            "zone_id": 1,
            "name": "Escalera",
            "description": None,
            "coordinates": [[0, 0], [1, 0], [1, 1], [0, 1]],
            "is_active": True,
            "camera_id": 1,
        }
    ]


def test_subjects(client):
    response = client.get("/api/sujetos")
    assert response.status_code == 200
    assert response.json() == [
        {"subject_id": 1, "name": "Rosa", "subject_type": "elderly", "description": None}
    ]


def test_camera_status_update(client):
    response = client.patch("/api/camaras/2/estado", json={"status": "maintenance"}, headers=KEY)
    assert response.status_code == 200
    assert response.json() == {"camera_id": 2, "status": "maintenance"}
    statuses = {c["camera_id"]: c["status"] for c in client.get("/api/camaras").json()}
    assert statuses == {1: "active", 2: "maintenance"}


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_camera_status_requires_the_iot_key(client, headers):
    response = client.patch("/api/camaras/1/estado", json={"status": "inactive"}, headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "X-API-Key inválida"}


def test_camera_status_of_unknown_camera(client):
    response = client.patch("/api/camaras/99/estado", json={"status": "inactive"}, headers=KEY)
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


@pytest.mark.parametrize("body", [{"status": "broken"}, {}])
def test_camera_status_must_be_valid(client, body):
    response = client.patch("/api/camaras/1/estado", json=body, headers=KEY)
    assert response.status_code == 422
