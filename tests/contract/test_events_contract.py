"""Contract: events registered by the IoT module and reviewed from the panel."""

import re

import pytest

from tests.contract.conftest import EVENT_KEYS, KEY, post_event


def test_register_minimal_event(client):
    response = client.post(
        "/api/eventos", json={"camera_id": 1, "event_type": "Caída"}, headers=KEY
    )
    assert response.status_code == 201
    event = response.json()
    assert set(event) == EVENT_KEYS
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", event["date"])
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", event["time"])
    assert event["occurred_at"] == f"{event['date']}T{event['time']}-05:00"
    assert {k: v for k, v in event.items() if k not in ("date", "time", "occurred_at")} == {
        "id": 1,
        "type": "Caída",
        "subject": "Persona sin identificar",
        "location": "Casa",
        "camera": "Sala",
        "priority": "Alto",
        "status": "Pendiente",
        "description": None,
    }


def test_register_complete_event(client):
    event = post_event(
        client,
        camera_id=1,
        event_type_id=2,
        subject_id=1,
        zone_id=1,
        detected_class="dog",
        confidence=0.5,
        evidence_url="https://example.com/evidencia.jpg",
        description="Merodeo en la escalera",
    )
    assert event["type"] == "Merodeo"
    assert event["subject"] == "Rosa"
    assert event["location"] == "Casa · Escalera"
    assert event["priority"] == "Medio"
    assert event["description"] == "Merodeo en la escalera"


def test_type_name_ignores_case_and_unknown_subject_uses_the_class(client):
    event = post_event(client, camera_id=2, event_type="humo", detected_class="cat")
    assert (event["type"], event["subject"], event["priority"]) == (
        "Humo",
        "Gato sin identificar",
        "Alto",
    )


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}])
def test_register_requires_the_iot_key(client, headers):
    response = client.post(
        "/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=headers
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "X-API-Key inválida"}


@pytest.mark.parametrize(
    "body",
    [
        {"camera_id": 99, "event_type_id": 1},
        {"camera_id": 1, "event_type_id": 99},
        {"camera_id": 1, "event_type": "Incendio"},
        {"camera_id": 1, "event_type_id": 1, "subject_id": 99},
        {"camera_id": 1, "event_type_id": 1, "zone_id": 99},
        {"camera_id": 2, "event_type_id": 1, "zone_id": 1},  # zone of another camera
    ],
)
def test_register_with_unknown_references(client, body):
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 404
    assert isinstance(response.json()["detail"], str)


def test_register_needs_an_event_type(client):
    response = client.post("/api/eventos", json={"camera_id": 1}, headers=KEY)
    assert response.status_code == 422
    assert response.json() == {"detail": "Envía event_type_id o event_type"}


@pytest.mark.parametrize(
    "body",
    [
        {"event_type_id": 1},
        {"camera_id": "uno", "event_type_id": 1},
        {"camera_id": 1, "event_type_id": 1, "confidence": 1.5},
        {"camera_id": 1, "event_type_id": 1, "detected_class": "robot"},
    ],
)
def test_register_validates_the_body(client, body):
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_get_event(client):
    created = post_event(client, camera_id=1, event_type_id=4, subject_id=1)
    response = client.get(f"/api/eventos/{created['id']}")
    assert response.status_code == 200
    assert response.json() == created


def test_get_unknown_event(client):
    response = client.get("/api/eventos/999")
    assert response.status_code == 404
    assert response.json() == {"detail": "Evento 999 no existe"}
    assert client.get("/api/eventos/abc").status_code == 422


def test_list_newest_first(client):
    ids = [
        post_event(client, camera_id=1, event_type_id=3)["id"],
        post_event(client, camera_id=2, event_type_id=1, subject_id=1)["id"],
        post_event(client, camera_id=1, event_type_id=2, zone_id=1)["id"],
    ]
    response = client.get("/api/eventos")
    assert response.status_code == 200
    events = response.json()
    assert [e["id"] for e in events] == ids[::-1]
    assert all(set(e) == EVENT_KEYS for e in events)


def test_list_filters(client):
    ruido = post_event(client, camera_id=1, event_type_id=3)
    caida = post_event(client, camera_id=2, event_type_id=1, subject_id=1)
    merodeo = post_event(client, camera_id=1, event_type_id=2, zone_id=1)
    client.patch(f"/api/eventos/{ruido['id']}/revisar")

    def ids(**params) -> list[int]:
        response = client.get("/api/eventos", params=params)
        assert response.status_code == 200
        return [e["id"] for e in response.json()]

    assert ids(prioridad="Alto") == [caida["id"]]
    assert ids(prioridad="Medio") == [merodeo["id"]]
    assert ids(estado="Revisado") == [ruido["id"]]
    assert ids(estado="Pendiente") == [merodeo["id"], caida["id"]]
    assert ids(estado="Pendiente", prioridad="Bajo") == []
    assert ids(q="rosa") == [caida["id"]]
    assert ids(q="ESCALERA") == [merodeo["id"]]
    assert ids(q=str(ruido["id"])) == [ruido["id"]]
    # Unknown labels are ignored, as the panel expects.
    assert ids(prioridad="Urgente", estado="Archivado") == [merodeo["id"], caida["id"], ruido["id"]]


def test_review_event(client):
    created = post_event(client, camera_id=1, event_type_id=1)
    response = client.patch(f"/api/eventos/{created['id']}/revisar")
    assert response.status_code == 200
    assert response.json() == created | {"status": "Revisado"}
    assert client.get(f"/api/eventos/{created['id']}").json()["status"] == "Revisado"


def test_review_is_idempotent(client):
    created = post_event(client, camera_id=1, event_type_id=1)
    first = client.patch(f"/api/eventos/{created['id']}/revisar")
    again = client.patch(f"/api/eventos/{created['id']}/revisar")
    assert again.status_code == 200
    assert again.json() == first.json()


def test_review_unknown_event(client):
    response = client.patch("/api/eventos/999/revisar")
    assert response.status_code == 404
    assert response.json() == {"detail": "Evento 999 no existe"}
