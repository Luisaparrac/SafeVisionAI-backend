import pytest

KEY = {"X-API-Key": "test-key"}


def test_list_cameras(client):
    response = client.get("/api/camaras")
    assert response.status_code == 200
    assert [(c["camera_id"], c["name"], c["ip_address"]) for c in response.json()] == [
        (1, "Sala", "192.0.2.1"),
        (2, "Patio", "192.0.2.2"),
    ]


def test_update_status_is_stored(client, uow):
    response = client.patch("/api/camaras/1/estado", json={"status": "disconnected"}, headers=KEY)
    assert response.status_code == 200
    assert response.json() == {"camera_id": 1, "status": "disconnected"}
    assert uow.cameras.get(1).status.value == "disconnected"


def test_update_status_requires_the_key_before_anything_else(client):
    response = client.patch("/api/camaras/99/estado", json={"status": "broken"})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("camera_id", "body", "status"),
    [(99, {"status": "inactive"}, 404), (1, {"status": "broken"}, 422), (1, {}, 422)],
)
def test_update_status_errors(client, camera_id, body, status):
    response = client.patch(f"/api/camaras/{camera_id}/estado", json=body, headers=KEY)
    assert response.status_code == status
