import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.security_headers import (
    SECURITY_HEADERS,
    SecurityHeadersMiddleware,
)

KEY = {"X-API-Key": "test-key"}


@pytest.mark.parametrize(
    ("method", "path", "kwargs"),
    [
        ("get", "/health", {}),
        ("get", "/api/eventos", {}),
        ("get", "/api/eventos/999", {}),  # 404
        ("post", "/api/eventos", {"json": {"camera_id": 1}}),  # 401 without key
        ("post", "/api/eventos", {"json": {"camera_id": 1}, "headers": KEY}),  # 422
        ("get", "/docs", {}),
    ],
)
def test_every_response_has_the_security_headers(client, method, path, kwargs):
    response = getattr(client, method)(path, **kwargs)
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value


def test_headers_set_by_an_endpoint_are_kept():
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/propio")
    def own() -> JSONResponse:
        return JSONResponse({}, headers={"Referrer-Policy": "same-origin"})

    response = TestClient(app).get("/propio")
    assert response.headers["referrer-policy"] == "same-origin"
    assert response.headers["x-frame-options"] == "DENY"
