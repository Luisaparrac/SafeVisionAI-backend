from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.body_limit import (
    MAX_BODY_BYTES,
    TOO_LARGE_MESSAGE,
    BodyLimitMiddleware,
)

KEY = {"X-API-Key": "test-key", "Content-Type": "application/json"}


def test_normal_requests_pass(client):
    response = client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    assert response.status_code == 201


def test_declared_size_over_the_limit_is_rejected_before_reading(client, uow):
    body = b'{"camera_id": 1, "event_type_id": 1, "description": "' + b"x" * MAX_BODY_BYTES + b'"}'
    response = client.post("/api/eventos", content=body, headers=KEY)
    assert response.status_code == 413
    assert response.json() == {"detail": TOO_LARGE_MESSAGE}
    assert response.headers["x-content-type-options"] == "nosniff"
    assert uow.events.all() == []


def test_body_without_declared_size_is_counted():
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware, max_bytes=10)

    @app.post("/eco")
    async def echo(request: Request) -> dict[str, int]:
        return {"bytes": len(await request.body())}

    client = TestClient(app)

    def chunks(total: int):
        for _ in range(total):
            yield b"x"

    assert client.post("/eco", content=chunks(10)).json() == {"bytes": 10}
    response = client.post("/eco", content=chunks(11))
    assert response.status_code == 413


def test_invalid_declared_size_is_rejected():
    app = FastAPI()
    app.add_middleware(BodyLimitMiddleware)

    @app.post("/eco")
    async def echo() -> dict[str, bool]:
        return {"ok": True}

    response = TestClient(app).post("/eco", content=b"{}", headers={"Content-Length": "-5"})
    assert response.status_code == 413
