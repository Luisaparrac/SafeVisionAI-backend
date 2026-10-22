"""Live alert feed for the panel over WebSocket (/ws/alertas).

``AlertBroadcaster`` implements the AlertNotifier port. The use cases call
``publish`` from the worker threads that run the HTTP endpoints, while each
WebSocket client lives in the event loop; every client has a bounded queue
fed with ``call_soon_threadsafe``, so publishing never blocks a request. A
client too slow to empty its queue loses messages instead of slowing others.

Clients authenticate with a ticket, the IoT key or the session cookie (see
``security.websocket_allowed``). Any other connection is accepted and closed at
once with code 4401, so the page can tell it apart from a network failure.

Messages (JSON, Spanish keys like the rest of the API):

* ``{"tipo": "alerta_nueva", "alerta": <AlertOut>}`` when an alert is raised;
* ``{"tipo": "evento_revisado", "evento": <EventOut>}`` when an event is
  reviewed or marked as a false alarm;
* ``{"tipo": "ping"}`` after ``KEEPALIVE_SECONDS`` without messages. Proxies
  close connections that carry no data, and browsers do not expose protocol
  pings to the page, so this lets the panel know the feed is alive. A send
  that fails also reveals a client that left without closing.
"""

import asyncio
import logging
import threading

from fastapi import APIRouter, WebSocket
from starlette.concurrency import run_in_threadpool

from safevision.adapters.inbound.http.schemas import AlertOut, EventOut
from safevision.adapters.inbound.http.security import websocket_allowed
from safevision.application.dto import NEW_ALERT, AlertNotification

logger = logging.getLogger(__name__)

QUEUE_SIZE = 100
KEEPALIVE_SECONDS = 25.0
PING = {"tipo": "ping"}
# Private range of WebSocket close codes (4000-4999), mirroring HTTP 401.
UNAUTHORIZED = 4401


def to_message(notification: AlertNotification) -> dict:
    if notification.kind == NEW_ALERT and notification.alert is not None:
        return {
            "tipo": "alerta_nueva",
            "alerta": AlertOut.from_view(notification.alert).model_dump(),
        }
    return {
        "tipo": "evento_revisado",
        "evento": EventOut.from_view(notification.event).model_dump(),
    }


class AlertBroadcaster:
    def __init__(self, queue_size: int = QUEUE_SIZE) -> None:
        self._queue_size = queue_size
        self._clients: dict[asyncio.Queue, asyncio.AbstractEventLoop] = {}
        self._lock = threading.Lock()

    def subscribe(self) -> asyncio.Queue:
        """Called from the event loop of a new client; returns its message queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=self._queue_size)
        with self._lock:
            self._clients[queue] = asyncio.get_running_loop()
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        with self._lock:
            self._clients.pop(queue, None)

    def publish(self, notification: AlertNotification) -> None:
        message = to_message(notification)
        with self._lock:
            clients = list(self._clients.items())
        for queue, loop in clients:
            try:
                loop.call_soon_threadsafe(self._offer, queue, message)
            except RuntimeError:  # the loop of that client is already closed
                self.unsubscribe(queue)

    @staticmethod
    def _offer(queue: asyncio.Queue, message: dict) -> None:
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning("websocket client too slow: message dropped")


router = APIRouter()


@router.websocket("/ws/alertas")
async def alerts_feed(websocket: WebSocket) -> None:
    container = websocket.app.state.container
    await websocket.accept()
    if not await run_in_threadpool(websocket_allowed, websocket, container):
        await websocket.close(code=UNAUTHORIZED, reason="No autenticado")
        return
    broadcaster: AlertBroadcaster = container.alert_broadcaster
    queue = broadcaster.subscribe()
    sender = asyncio.create_task(_forward(queue, websocket))
    receiver = asyncio.create_task(_until_disconnect(websocket))
    try:
        await asyncio.wait({sender, receiver}, return_when=asyncio.FIRST_COMPLETED)
    finally:
        sender.cancel()
        receiver.cancel()
        broadcaster.unsubscribe(queue)


async def _forward(queue: asyncio.Queue, websocket: WebSocket) -> None:
    while True:
        try:
            message = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SECONDS)
        except TimeoutError:
            message = PING
        await websocket.send_json(message)


async def _until_disconnect(websocket: WebSocket) -> None:
    # Messages from the client are ignored; reading is how a disconnection is noticed.
    while (await websocket.receive())["type"] != "websocket.disconnect":
        pass
