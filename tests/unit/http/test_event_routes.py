import pytest

KEY = {"X-API-Key": "test-key"}


def post(client, **body):
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 201, response.text
    return response.json()


def test_register_and_get(client):
    created = post(client, camera_id=1, event_type="caída", zone_id=1, subject_id=1)
    assert created["location"] == "Casa · Escalera"
    assert created["subject"] == "Rosa"
    assert client.get(f"/api/eventos/{created['id']}").json() == created


def test_register_uses_the_clock_in_the_configured_time_zone(client):
    # FakeClock starts at 12:00 UTC, which is 07:00 in Bogotá.
    created = post(client, camera_id=1, event_type_id=1)
    assert (created["date"], created["time"]) == ("2026-10-14", "07:00:00")


def test_register_requires_the_key(client):
    response = client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1})
    assert response.status_code == 401


@pytest.mark.parametrize(
    ("body", "status"),
    [
        ({"camera_id": 99, "event_type_id": 1}, 404),
        ({"camera_id": 2, "event_type_id": 1, "zone_id": 1}, 404),
        ({"camera_id": 1}, 422),
        ({"camera_id": 1, "event_type_id": 1, "confidence": 2}, 422),
    ],
)
def test_register_errors(client, body, status):
    assert client.post("/api/eventos", json=body, headers=KEY).status_code == status


def test_list_with_filters(client, clock):
    ruido = post(client, camera_id=1, event_type_id=3)
    clock.advance(60)
    caida = post(client, camera_id=2, event_type_id=1, subject_id=1)
    assert [e["id"] for e in client.get("/api/eventos").json()] == [caida["id"], ruido["id"]]
    alto = client.get("/api/eventos", params={"prioridad": "Alto"}).json()
    assert [e["id"] for e in alto] == [caida["id"]]
    assert client.get("/api/eventos", params={"q": "rosa"}).json() == [caida]
    assert client.get("/api/eventos", params={"estado": "Revisado"}).json() == []


def test_recent_is_not_taken_as_an_id(client):
    created = post(client, camera_id=1, event_type_id=2)
    response = client.get("/api/eventos/recientes", params={"limit": 5})
    assert response.status_code == 200
    assert response.json() == [created]


def test_review(client):
    created = post(client, camera_id=1, event_type_id=1)
    response = client.patch(f"/api/eventos/{created['id']}/revisar")
    assert response.status_code == 200
    assert response.json()["status"] == "Revisado"
    assert client.patch("/api/eventos/999/revisar").status_code == 404
