"""Contract: pending alerts (priority queue), panel metrics and recent history."""

import pytest

from tests.contract.conftest import EVENT_KEYS, post_event

pytestmark = pytest.mark.integration


@pytest.fixture
def events(client) -> dict[str, dict]:
    """Four events with different severities and no repeated detections."""
    return {
        "ruido": post_event(client, camera_id=1, event_type_id=3),  # severity 1
        "caida": post_event(client, camera_id=1, event_type_id=1, subject_id=1),  # 4
        "merodeo": post_event(client, camera_id=2, event_type_id=2),  # 2
        "humo": post_event(client, camera_id=2, event_type_id=4),  # 3
    }


def test_nothing_pending_at_start(client):
    assert client.get("/api/alertas/pendientes").json() == []
    assert client.get("/api/metricas").json() == {"total": 0, "pendientes": 0, "alto": 0}
    assert client.get("/api/eventos/recientes").json() == []


def test_pending_alerts_most_severe_first(client, events):
    response = client.get("/api/alertas/pendientes")
    assert response.status_code == 200
    alerts = response.json()
    assert [a["event"] for a in alerts] == [
        events["caida"],
        events["humo"],
        events["merodeo"],
        events["ruido"],
    ]
    assert [a["nivel"] for a in alerts] == ["Alto", "Alto", "Medio", "Bajo"]
    assert alerts[0] == {
        "id_alerta": 2,
        "nivel": "Alto",
        "estado": "Activa",
        "event": events["caida"],
    }
    assert all(set(a) == {"id_alerta", "nivel", "estado", "event"} for a in alerts)
    assert all(set(a["event"]) == EVENT_KEYS for a in alerts)


def test_pending_alerts_limit(client, events):
    response = client.get("/api/alertas/pendientes", params={"limit": 2})
    assert [a["event"]["id"] for a in response.json()] == [
        events["caida"]["id"],
        events["humo"]["id"],
    ]


@pytest.mark.parametrize("limit", [0, 101, "diez"])
def test_pending_alerts_limit_is_validated(client, limit):
    assert client.get("/api/alertas/pendientes", params={"limit": limit}).status_code == 422


def test_reviewed_event_leaves_the_queue(client, events):
    client.patch(f"/api/eventos/{events['caida']['id']}/revisar")
    pending = [a["event"]["id"] for a in client.get("/api/alertas/pendientes").json()]
    assert pending == [events["humo"]["id"], events["merodeo"]["id"], events["ruido"]["id"]]


def test_metrics(client, events):
    assert client.get("/api/metricas").json() == {"total": 4, "pendientes": 4, "alto": 2}
    client.patch(f"/api/eventos/{events['humo']['id']}/revisar")
    response = client.get("/api/metricas")
    assert response.status_code == 200
    assert response.json() == {"total": 4, "pendientes": 3, "alto": 2}


def test_recent_events_newest_first(client, events):
    response = client.get("/api/eventos/recientes")
    assert response.status_code == 200
    assert response.json() == [events["humo"], events["merodeo"], events["caida"], events["ruido"]]
    limited = client.get("/api/eventos/recientes", params={"limit": 2}).json()
    assert limited == [events["humo"], events["merodeo"]]


def test_recent_history_shows_the_review(client, events):
    client.patch(f"/api/eventos/{events['ruido']['id']}/revisar")
    recent = {e["id"]: e for e in client.get("/api/eventos/recientes").json()}
    assert recent[events["ruido"]["id"]] == events["ruido"] | {"status": "Revisado"}


@pytest.mark.parametrize("limit", [0, 101])
def test_recent_events_limit_is_validated(client, limit):
    assert client.get("/api/eventos/recientes", params={"limit": limit}).status_code == 422
