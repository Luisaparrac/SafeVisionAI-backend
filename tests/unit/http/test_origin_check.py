"""CSRF protection: changes sent with the session cookie must come from a trusted origin."""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.security import ensure_trusted_origin


@pytest.fixture
def checked(container) -> TestClient:
    app = FastAPI()

    @app.api_route("/cambio", methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"])
    def cambio(request: Request) -> dict[str, bool]:
        ensure_trusted_origin(request, container)
        return {"ok": True}

    return TestClient(app, base_url="https://api.example.com")


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
@pytest.mark.parametrize(
    "headers",
    [
        {"Origin": "http://localhost:5173"},
        {"Origin": "http://localhost:5173/"},
        {"Referer": "http://localhost:5173/eventos?id=3"},
        # The backend itself (the /docs page), seen over http behind the proxy.
        {"Origin": "https://api.example.com"},
        {"Origin": "http://api.example.com"},
        {"Referer": "https://api.example.com/docs"},
    ],
)
def test_trusted_origins_pass(checked, method, headers):
    assert checked.request(method, "/cambio", headers=headers).status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Origin": "https://evil.example"},
        {"Origin": "null"},
        {"Origin": "http://localhost:5174"},
        {"Origin": "https://api.example.com.evil.example"},
        {"Referer": "https://evil.example/http://localhost:5173"},
        {"Referer": "no es una url"},
        # Origin wins over Referer when both are present.
        {"Origin": "https://evil.example", "Referer": "http://localhost:5173/"},
    ],
)
def test_other_origins_are_refused(checked, headers):
    response = checked.patch("/cambio", headers=headers)
    assert response.status_code == 403
    assert response.json() == {"detail": "Origen no permitido"}


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_reads_are_not_checked(checked, method):
    response = checked.request(method, "/cambio", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
