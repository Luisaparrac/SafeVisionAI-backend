import asyncio
import threading

from safevision.adapters.inbound.http.websocket import AlertBroadcaster, to_message
from safevision.application.dto import (
    EVENT_CLOSED,
    NEW_ALERT,
    AlertNotification,
    AlertView,
    EventView,
)

KEY = {"X-API-Key": "test-key"}

VIEW = EventView(
    id=1,
    type="Caída",
    subject="Rosa",
    location="Casa",
    camera="Sala",
    date="2026-10-14",
    time="07:00:00",
    priority="Alto",
    status="Pendiente",
    description=None,
)


def test_feed_sends_new_alerts_and_closed_events(client):
    with client.websocket_connect("/ws/alertas") as feed:
        created = client.post(
            "/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY
        ).json()
        assert feed.receive_json() == {
            "tipo": "alerta_nueva",
            "alerta": {"id_alerta": 1, "nivel": "Alto", "estado": "Activa", "event": created},
        }
        reviewed = client.patch(f"/api/eventos/{created['id']}/revisar").json()
        assert feed.receive_json() == {"tipo": "evento_revisado", "evento": reviewed}


def test_every_client_gets_the_message(client):
    with (
        client.websocket_connect("/ws/alertas") as first,
        client.websocket_connect("/ws/alertas") as second,
    ):
        client.post("/api/eventos", json={"camera_id": 2, "event_type_id": 3}, headers=KEY)
        assert first.receive_json()["tipo"] == "alerta_nueva"
        assert second.receive_json()["tipo"] == "alerta_nueva"


def test_disconnected_clients_are_forgotten(client, container):
    with client.websocket_connect("/ws/alertas") as feed:
        feed.send_text("hola")  # client messages are ignored
        client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 2}, headers=KEY)
        feed.receive_json()
        assert len(container.alert_broadcaster._clients) == 1
    deadline = 50
    while len(container.alert_broadcaster._clients) and deadline:
        threading.Event().wait(0.05)
        deadline -= 1
    assert len(container.alert_broadcaster._clients) == 0


def test_messages():
    alert = AlertView(alert_id=4, level="Alto", status="Activa", event=VIEW)
    assert to_message(AlertNotification(NEW_ALERT, VIEW, alert))["alerta"]["id_alerta"] == 4
    closed = to_message(AlertNotification(EVENT_CLOSED, VIEW))
    assert closed == {"tipo": "evento_revisado", "evento": closed["evento"]}
    assert closed["evento"]["id"] == 1


def test_publish_from_another_thread_reaches_the_loop():
    broadcaster = AlertBroadcaster()

    async def scenario():
        queue = broadcaster.subscribe()
        thread = threading.Thread(
            target=broadcaster.publish, args=(AlertNotification(EVENT_CLOSED, VIEW),)
        )
        thread.start()
        message = await asyncio.wait_for(queue.get(), timeout=5)
        thread.join()
        return message

    assert asyncio.run(scenario())["tipo"] == "evento_revisado"


def test_slow_client_loses_messages_without_blocking():
    broadcaster = AlertBroadcaster(queue_size=2)

    async def scenario():
        queue = broadcaster.subscribe()
        for _ in range(5):
            broadcaster.publish(AlertNotification(EVENT_CLOSED, VIEW))
        await asyncio.sleep(0)  # let the scheduled deliveries run
        return queue.qsize()

    assert asyncio.run(scenario()) == 2


def test_publishing_without_clients_or_with_a_closed_loop_never_raises():
    broadcaster = AlertBroadcaster()
    broadcaster.publish(AlertNotification(EVENT_CLOSED, VIEW))

    async def subscribe():
        return broadcaster.subscribe()

    asyncio.run(subscribe())  # its loop is closed when run() returns
    broadcaster.publish(AlertNotification(EVENT_CLOSED, VIEW))
    assert len(broadcaster._clients) == 0


def test_idle_feed_sends_keepalive_pings(client, monkeypatch):
    import safevision.adapters.inbound.http.websocket as websocket

    monkeypatch.setattr(websocket, "KEEPALIVE_SECONDS", 0.05)
    with client.websocket_connect("/ws/alertas") as feed:
        assert feed.receive_json() == {"tipo": "ping"}
        assert feed.receive_json() == {"tipo": "ping"}
        # A real message still arrives between pings.
        client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 4}, headers=KEY)
        kinds = [feed.receive_json()["tipo"] for _ in range(5)]
        assert "alerta_nueva" in kinds
        assert set(kinds) <= {"ping", "alerta_nueva"}
