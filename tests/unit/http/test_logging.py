import logging
import sys

import pytest

from safevision.adapters.inbound.http.logging_setup import (
    FORMAT,
    LOGGER_NAME,
    RedactingFormatter,
    configure_logging,
    redact,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "no conecta a postgresql://user:s3cret@db.example.com:5432/prod",
            "no conecta a postgresql://***@db.example.com:5432/prod",
        ),
        ("postgres://solo-usuario@host/db", "postgres://***@host/db"),
        ("X-API-Key: abc123", "X-API-Key: ***"),
        ("{'x-api-key': 'abc123'}", "{'x-api-key': '***'}"),
        ("password=hunter2&user=a", "password=***&user=a"),
        ("IOT_API_KEY=clave larga", "IOT_API_KEY=*** larga"),
        ("GET /api/eventos 200", "GET /api/eventos 200"),
        ("visita https://example.com/docs", "visita https://example.com/docs"),
    ],
)
def test_redact(text, expected):
    assert redact(text) == expected


def test_tracebacks_are_redacted_too():
    formatter = RedactingFormatter(FORMAT)
    try:
        raise RuntimeError("fallo con postgresql://u:p4ss@h/db")
    except RuntimeError:
        record = logging.LogRecord("safevision", logging.ERROR, __file__, 1, "x", None, True)
        record.exc_info = sys.exc_info()
    line = formatter.format(record)
    assert "p4ss" not in line
    assert "request_id=-" in line


@pytest.fixture
def restore_logging():
    logger = logging.getLogger(LOGGER_NAME)
    saved = logger.handlers[:], logger.level, logger.propagate
    access = logging.getLogger("uvicorn.access").disabled
    yield
    logger.handlers[:], logger.level, logger.propagate = saved
    logging.getLogger("uvicorn.access").disabled = access


def test_configure_logging(restore_logging):
    configure_logging("WARNING")
    logger = logging.getLogger(LOGGER_NAME)
    assert logger.level == logging.WARNING
    assert isinstance(logger.handlers[0].formatter, RedactingFormatter)
    assert logging.getLogger("uvicorn.access").disabled


def test_access_log_has_request_id_but_no_query_string(client, caplog):
    with caplog.at_level(logging.INFO, logger="safevision.http"):
        response = client.get("/api/eventos?q=Rosa", headers={"X-Request-ID": "req-1"})
    [record] = [r for r in caplog.records if r.name == "safevision.http"]
    message = record.getMessage()
    assert message.startswith("method=GET path=/api/eventos status=200 duration_ms=")
    assert "Rosa" not in message
    assert response.headers["x-request-id"] == "req-1"
    assert RedactingFormatter(FORMAT).format(record).count("request_id=req-1") == 1
