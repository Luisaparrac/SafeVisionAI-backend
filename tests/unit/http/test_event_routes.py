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


def test_repeated_detection_returns_the_same_event_marked_as_duplicate(client, clock, uow):
    first = client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    assert "x-duplicate" not in first.headers
    clock.advance(3)
    again = client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    assert again.status_code == 201
    assert again.headers["x-duplicate"] == "true"
    assert again.json() == first.json()
    assert len(uow.events.all()) == 1


def test_detection_after_the_window_is_a_new_event(client, clock, settings):
    first = post(client, camera_id=1, event_type_id=1)
    clock.advance(settings.dedup_window_seconds)
    response = client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    assert "x-duplicate" not in response.headers
    assert response.json()["id"] != first["id"]


def test_browsers_can_read_the_duplicate_header(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "X-Duplicate" in response.headers["access-control-expose-headers"]


def test_oversized_description_is_rejected_before_storing(client, uow):
    body = {"camera_id": 1, "event_type_id": 1, "description": "x" * 2001}
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 422
    assert uow.events.all() == []


def test_filter_by_camera(client, clock):
    sala = post(client, camera_id=1, event_type_id=3)
    clock.advance(1)
    patio = post(client, camera_id=2, event_type_id=3)
    assert client.get("/api/eventos", params={"camara_id": 2}).json() == [patio]
    assert client.get("/api/eventos", params={"camara_id": 1}).json() == [sala]
    assert client.get("/api/eventos", params={"camara_id": 99}).json() == []
    combined = client.get("/api/eventos", params={"camara_id": 1, "prioridad": "Alto"})
    assert combined.json() == []
    assert client.get("/api/eventos", params={"camara_id": "sala"}).status_code == 422


def test_filter_by_dates(client, clock):
    # FakeClock: 2026-10-14 12:00 UTC, 07:00 in Bogotá.
    today = post(client, camera_id=1, event_type_id=3)
    clock.advance(24 * 3600)
    tomorrow = post(client, camera_id=1, event_type_id=3)
    params = {"desde": "2026-10-14", "hasta": "2026-10-14"}
    assert client.get("/api/eventos", params=params).json() == [today]
    assert client.get("/api/eventos", params={"desde": "2026-10-15"}).json() == [tomorrow]
    reversed_range = client.get(
        "/api/eventos", params={"desde": "2026-10-15", "hasta": "2026-10-14"}
    )
    assert reversed_range.status_code == 422
    assert client.get("/api/eventos", params={"desde": "14/10/2026"}).status_code == 422


def test_pagination_is_optional(client, clock):
    created = []
    for event_type_id in (1, 2, 3, 4):
        created.append(post(client, camera_id=1, event_type_id=event_type_id))
        clock.advance(1)
    newest_first = [e["id"] for e in reversed(created)]
    assert [e["id"] for e in client.get("/api/eventos").json()] == newest_first
    page = client.get("/api/eventos", params={"limit": 2, "offset": 1}).json()
    assert [e["id"] for e in page] == newest_first[1:3]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 501}, {"offset": -1}])
def test_pagination_bounds(client, params):
    assert client.get("/api/eventos", params=params).status_code == 422
