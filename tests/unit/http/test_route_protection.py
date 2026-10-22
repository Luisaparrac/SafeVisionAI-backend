"""Every /api route needs a session or the IoT key, except logging in and out.

The routes are read from the OpenAPI schema of the application itself, so a new
route that forgets its protection fails here.
"""

import re

import pytest

from safevision.adapters.inbound.http.app import create_app
from safevision.bootstrap import build_container
from safevision.config.settings import Settings
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork

KEY = {"X-API-Key": "test-key"}
OPEN = {("POST", "/api/auth/login"), ("POST", "/api/auth/logout")}
# Only the IoT module calls these; a panel session is not enough.
IOT_ONLY = {("POST", "/api/eventos"), ("PATCH", "/api/camaras/{camera_id}/estado")}


def api_routes() -> list[tuple[str, str]]:
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        iot_api_key="test-key",
        session_secret="test-session-secret-0123456789abcdef",
    )
    app = create_app(build_container(settings, FakeUnitOfWork(), FakeClock()))
    return sorted(
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith("/api")
        for method in operations
    )


ROUTES = api_routes()
PROTECTED = [route for route in ROUTES if route not in OPEN]


def concrete(path: str) -> str:
    return re.sub(r"\{\w+\}", "1", path)


def test_the_open_routes_exist():
    assert set(ROUTES) >= OPEN | IOT_ONLY


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_without_credentials_every_api_route_answers_401(anonymous, method, path):
    assert anonymous.request(method, concrete(path)).status_code == 401


@pytest.mark.parametrize(("method", "path"), sorted(IOT_ONLY))
def test_a_session_is_not_enough_for_the_iot_routes(client, method, path):
    response = client.request(method, concrete(path), json={})
    assert response.status_code == 401
    assert response.json() == {"detail": "X-API-Key inválida"}


@pytest.mark.parametrize(
    "path", ["/api/tipos-evento", "/api/ubicaciones", "/api/camaras", "/api/zonas", "/api/sujetos"]
)
def test_the_iot_key_reads_the_catalogs(anonymous, path):
    assert anonymous.get(path, headers=KEY).status_code == 200


def test_a_wrong_key_is_not_a_credential(anonymous):
    response = anonymous.get("/api/tipos-evento", headers={"X-API-Key": "otra"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Inicia sesión para continuar"}


def test_changes_with_the_key_skip_the_origin_check(anonymous):
    anonymous.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    response = anonymous.patch(
        "/api/eventos/1/revisar", headers=KEY | {"Origin": "https://evil.example"}
    )
    assert response.status_code == 200


def test_changes_with_the_cookie_check_the_origin(client):
    client.post("/api/eventos", json={"camera_id": 1, "event_type_id": 1}, headers=KEY)
    evil = client.patch("/api/eventos/1/revisar", headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    assert evil.json() == {"detail": "Origen no permitido"}
    # Reading from the panel is still fine, and the event was not reviewed.
    assert client.get("/api/eventos/1").json()["status"] == "Pendiente"
    assert client.patch("/api/eventos/1/revisar").json()["status"] == "Revisado"


@pytest.mark.parametrize("path", ["/", "/health", "/health/ready", "/docs", "/openapi.json"])
def test_public_routes(anonymous, path):
    assert anonymous.get(path).status_code == 200


def test_openapi_documents_the_protection(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "401" in paths["/api/eventos"]["get"]["responses"]
    assert "401" in paths["/api/tipos-evento"]["get"]["responses"]
