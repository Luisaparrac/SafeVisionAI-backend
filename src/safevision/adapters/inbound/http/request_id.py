"""Request identifier: one id per request, returned in X-Request-ID and added to the logs.

A client (or a proxy) may send its own id to correlate logs; it is accepted
only if it is short and made of safe characters, otherwise a new one is made.
"""

import re
import uuid
from contextvars import ContextVar

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")

_current: ContextVar[str | None] = ContextVar("request_id", default=None)


def current_request_id() -> str | None:
    """Id of the request being handled in this context, or None outside a request."""
    return _current.get()


def accepted_id(candidate: str | None) -> str:
    if candidate is not None and _VALID_ID.fullmatch(candidate):
        return candidate
    return uuid.uuid4().hex


class RequestIdMiddleware:
    """Pure ASGI middleware, so the id is visible to sync endpoints run in threads."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request_id = accepted_id(Headers(scope=scope).get(REQUEST_ID_HEADER))
        token = _current.set(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _current.reset(token)
