import re

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.request_id import (
    RequestIdMiddleware,
    accepted_id,
    current_request_id,
)


def test_every_response_carries_a_new_id(client):
    first = client.get("/health").headers["x-request-id"]
    second = client.get("/health").headers["x-request-id"]
    assert re.fullmatch(r"[0-9a-f]{32}", first)
    assert first != second


def test_a_safe_incoming_id_is_kept(client):
    response = client.get("/health", headers={"X-Request-ID": "proxy-123.abc_DEF"})
    assert response.headers["x-request-id"] == "proxy-123.abc_DEF"


@pytest.mark.parametrize("candidate", [None, "", "a" * 65, "id con espacios", "x\r\nSet-Cookie"])
def test_unsafe_incoming_ids_are_replaced(candidate):
    assert re.fullmatch(r"[0-9a-f]{32}", accepted_id(candidate))


def test_error_responses_also_carry_the_id(client):
    assert "x-request-id" in client.get("/api/eventos/999").headers


def test_browsers_can_read_the_id(client):
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert "X-Request-ID" in response.headers["access-control-expose-headers"]


def test_sync_endpoints_see_the_id_of_their_request():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/id")
    def read_id() -> dict[str, str | None]:
        return {"id": current_request_id()}

    response = TestClient(app).get("/id", headers={"X-Request-ID": "abc"})
    assert response.json() == {"id": "abc"}
    assert current_request_id() is None
