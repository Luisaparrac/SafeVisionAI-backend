"""Logging in key=value lines, with the request id and without sensitive data.

Every line goes through ``redact`` before it is written, tracebacks included:
credentials in connection URLs and values of fields such as the API key or a
password are masked. The access log records method, path, status and
duration; it leaves out the query string and the client address.
"""

import logging
import re
import sys
import time

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from safevision.adapters.inbound.http.request_id import current_request_id

LOGGER_NAME = "safevision"
FORMAT = "%(asctime)s level=%(levelname)s logger=%(name)s request_id=%(request_id)s %(message)s"
MASK = "***"

_URL_CREDENTIALS = re.compile(r"([a-z][a-z0-9+.-]*://)[^\s/@]+@", re.IGNORECASE)
_SECRET_FIELDS = re.compile(
    r"\b([\w-]*?(?:api[_-]?key|password|passwd|secret|token))(['\"]?\s*[:=]\s*['\"]?)[^\s'\",;&]+",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    text = _URL_CREDENTIALS.sub(rf"\g<1>{MASK}@", text)
    return _SECRET_FIELDS.sub(rf"\g<1>\g<2>{MASK}", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if getattr(record, "request_id", None) is None:
            record.request_id = current_request_id() or "-"
        return redact(super().format(record))


def configure_logging(level: str = "INFO") -> None:
    """Sends the application logs to stdout, where the hosting platform collects them."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(RedactingFormatter(FORMAT))
    logger = logging.getLogger(LOGGER_NAME)
    logger.handlers[:] = [handler]
    logger.setLevel(level)
    logger.propagate = False
    # Replaced by the access log below, which omits the query string and the client IP.
    logging.getLogger("uvicorn.access").disabled = True


class AccessLogMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(f"{LOGGER_NAME}.http")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = time.perf_counter()
        status = 500  # if the application fails before answering

        async def record_status(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, record_status)
        finally:
            self.logger.info(
                "method=%s path=%s status=%d duration_ms=%.1f",
                scope["method"],
                scope["path"],
                status,
                (time.perf_counter() - started) * 1000,
                extra={"request_id": current_request_id()},
            )
