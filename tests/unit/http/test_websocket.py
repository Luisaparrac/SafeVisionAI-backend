import asyncio
import threading

import pytest
from starlette.websockets import WebSocketDisconnect

from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE
from safevision.adapters.inbound.http.websocket import AlertBroadcaster, to_message
from safevision.application.dto import (
    EVENT_CLOSED,
    NEW_ALERT,
    AlertNotification,
    AlertView,
    EventView,
)

KEY = {"X-API-Key": "test-key"}


def feed(client):
    """Opens the feed as the panel page does: with a ticket of its session."""
    ticket = client.get("/api/auth/ws-ticket").json()["ticket"]
    return client.websocket_connect(f"/ws/alertas?ticket={ticket}")


VIEW = EventView(
    id=1,
    type="Caída",
    subject="Rosa",
    location="Casa",
    camera="Sala",
    date="2026-10-14",
    time="07:00:00",
    occurred_at="2026-10-14T07:00:00-05:00",
    priority="Alto",
    status="Pendiente",
    description=None,
)


def test_feed_sends_new_alerts_and_closed_events(client):
    with feed(client) as feed_:
        created = client.post(
            "/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY
        ).json()
        assert feed_.receive_json() == {
            "tipo": "alerta_nueva",
            "alerta": {"id_alerta": 1, "nivel": "Alto", "estado": "Activa", "event": created},
        }
        reviewed = client.patch(f"/api/eventos/{created['id']}/revisar").json()
        assert feed_.receive_json() == {"tipo": "evento_revisado", "evento": reviewed}


def test_every_client_gets_the_message(client):
    with (
        feed(client) as first,
        feed(client) as second,
    ):
        client.post("/api/eventos", json={"camera_id": 2, "event_type_id": 3}, headers=KEY)
        assert first.receive_json()["tipo"] == "alerta_nueva"
        assert second.receive_json()["tipo"] == "alerta_nueva"


def test_disconnected_clients_are_forgotten(client, container):
    with feed(client) as feed_:
        feed_.send_text("hola")  # client messages are ignored
        client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 2}, headers=KEY)
        feed_.receive_json()
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
    with feed(client) as feed_:
        assert feed_.receive_json() == {"tipo": "ping"}
        assert feed_.receive_json() == {"tipo": "ping"}
        # A real message still arrives between pings.
        client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 4}, headers=KEY)
        kinds = [feed_.receive_json()["tipo"] for _ in range(5)]
        assert "alerta_nueva" in kinds
        assert set(kinds) <= {"ping", "alerta_nueva"}


def closed_code(client, url: str, **kwargs) -> int:
    with pytest.raises(WebSocketDisconnect) as info, client.websocket_connect(url, **kwargs) as ws:
        ws.receive_json()
    return info.value.code


def test_feed_without_credentials_is_closed_with_4401(anonymous, container):
    assert closed_code(anonymous, "/ws/alertas") == 4401
    assert len(container.alert_broadcaster._clients) == 0


def test_ticket_from_a_session(client):
    response = client.get("/api/auth/ws-ticket")
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"ticket", "expires_in"}
    assert body["expires_in"] == 60


def test_ticket_requires_a_session(anonymous):
    assert anonymous.get("/api/auth/ws-ticket").status_code == 401
    # The IoT key reads the catalogs, but tickets are only for panel users.
    assert anonymous.get("/api/auth/ws-ticket", headers=KEY).status_code == 401


def test_ticket_expires_after_60_seconds(client, clock):
    ticket = client.get("/api/auth/ws-ticket").json()["ticket"]
    clock.advance(60)
    assert closed_code(client, f"/ws/alertas?ticket={ticket}") == 4401


def test_ticket_of_a_removed_user_is_refused(client, uow):
    ticket = client.get("/api/auth/ws-ticket").json()["ticket"]
    uow.users._rows.pop(1)
    assert closed_code(client, f"/ws/alertas?ticket={ticket}") == 4401


def test_ticket_is_not_a_session_and_a_session_is_not_a_ticket(client, container):
    ticket = client.get("/api/auth/ws-ticket").json()["ticket"]
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, ticket)
    assert client.get("/api/auth/me").status_code == 401
    session = container.sessions.signer.issue(1, SESSION, container.sessions.lifetime)
    assert closed_code(client, f"/ws/alertas?ticket={session}") == 4401


def test_feed_with_the_iot_key(anonymous):
    with anonymous.websocket_connect("/ws/alertas", headers=dict(KEY)) as feed_:
        anonymous.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
        assert feed_.receive_json()["tipo"] == "alerta_nueva"
    wrong = {"X-API-Key": "otra"}
    assert closed_code(anonymous, "/ws/alertas", headers=wrong) == 4401


def session_cookie(container) -> str:
    token = container.sessions.signer.issue(1, SESSION, container.sessions.lifetime)
    return f"{SESSION_COOKIE}={token}"


def test_feed_with_the_session_cookie_from_the_panel(anonymous, container):
    headers = {"cookie": session_cookie(container), "origin": "http://localhost:5173"}
    with anonymous.websocket_connect("/ws/alertas", headers=headers) as feed_:
        anonymous.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
        assert feed_.receive_json()["tipo"] == "alerta_nueva"


@pytest.mark.parametrize("origin", ["https://evil.example", "null"])
def test_session_cookie_from_another_site_is_refused(anonymous, container, origin):
    # Cross-site WebSocket hijacking: the browser would send the cookie anyway.
    headers = {"cookie": session_cookie(container), "origin": origin}
    assert closed_code(anonymous, "/ws/alertas", headers=headers) == 4401


def test_session_cookie_without_origin_is_refused(container):
    from fastapi.testclient import TestClient

    from safevision.adapters.inbound.http.app import create_app

    with TestClient(create_app(container)) as plain:  # sends no Origin
        headers = {"cookie": session_cookie(container)}
        assert closed_code(plain, "/ws/alertas", headers=headers) == 4401


def test_forged_cookie_is_refused(anonymous):
    headers = {"cookie": f"{SESSION_COOKIE}=falsa", "origin": "http://localhost:5173"}
    assert closed_code(anonymous, "/ws/alertas", headers=headers) == 4401
