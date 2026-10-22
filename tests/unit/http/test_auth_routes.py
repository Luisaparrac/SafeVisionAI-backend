import pytest

from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE
from tests.fakes.users import TEST_EMAIL, TEST_NAME, TEST_PASSWORD

SESSION_BODY = {
    "authenticated": True,
    "user": {"id": 1, "name": TEST_NAME, "email": TEST_EMAIL},
}
WRONG = {"detail": "Correo o contraseña incorrectos"}
PANEL = {"Origin": "http://localhost:5173"}


@pytest.fixture
def client(anonymous):
    """These tests start without a session."""
    return anonymous


def login(client, email=TEST_EMAIL, password=TEST_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def test_login_returns_the_user_and_sets_the_cookie(client, container):
    response = login(client, email=" USUARIO@Example.com ")
    assert response.status_code == 200
    assert response.json() == SESSION_BODY
    token = response.cookies[SESSION_COOKIE]
    assert container.sessions.signer.read(token, SESSION) == 1


def test_session_cookie_attributes(client):
    header = login(client).headers["set-cookie"]
    attributes = {part.strip().split("=")[0].lower() for part in header.split(";")}
    assert header.startswith(f"{SESSION_COOKIE}=")
    assert {"httponly", "secure", "path", "max-age", "samesite"} <= attributes
    assert "domain" not in attributes
    assert "Path=/" in header
    assert "SameSite=none" in header
    assert "Max-Age=28800" in header  # SESSION_TTL_HOURS = 8


def test_same_site_comes_from_the_settings(settings, uow, clock):
    from dataclasses import replace

    from fastapi.testclient import TestClient

    from safevision.adapters.inbound.http.app import create_app
    from safevision.bootstrap import build_container
    from tests.fakes.users import FAST_HASHER

    lax = replace(settings, session_cookie_samesite="lax", session_ttl_hours=1)
    container = build_container(lax, uow, clock, password_hasher=FAST_HASHER)
    with TestClient(create_app(container), base_url="https://testserver") as client:
        header = login(client).headers["set-cookie"]
    assert "SameSite=lax" in header
    assert "Max-Age=3600" in header


@pytest.mark.parametrize(
    ("email", "password"),
    [
        (TEST_EMAIL, "otra-clave"),
        (TEST_EMAIL, TEST_PASSWORD.upper()),
        ("nadie@example.com", TEST_PASSWORD),
    ],
)
def test_wrong_credentials_get_the_same_answer(client, email, password):
    response = login(client, email, password)
    assert response.status_code == 401
    assert response.json() == WRONG
    assert SESSION_COOKIE not in response.cookies


@pytest.mark.parametrize(
    "body",
    [{}, {"email": TEST_EMAIL}, {"password": "x"}, {"email": "a" * 321, "password": "x"}],
)
def test_invalid_bodies_are_rejected(client, body):
    assert client.post("/api/auth/login", json=body).status_code == 422


def test_very_long_passwords_are_rejected_before_hashing(client):
    response = login(client, password="x" * 1025)
    assert response.status_code == 422


def test_openapi_describes_the_login(client):
    operation = client.get("/openapi.json").json()["paths"]["/api/auth/login"]["post"]
    assert operation["summary"] == "Iniciar sesión"
    assert "401" in operation["responses"]


def test_me_returns_the_session_user(client):
    login(client)
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json() == SESSION_BODY


def test_me_without_a_session(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Inicia sesión para continuar"}


def test_me_with_a_forged_cookie(client):
    token = login(client).cookies[SESSION_COOKIE]
    client.cookies.clear()
    client.cookies.set(SESSION_COOKIE, token[:-2] + "xx")
    assert client.get("/api/auth/me").status_code == 401


def test_session_expires_after_its_lifetime(client, clock):
    login(client)
    clock.advance(8 * 3600 - 1)
    assert client.get("/api/auth/me").status_code == 200
    clock.advance(1)
    assert client.get("/api/auth/me").status_code == 401


def test_session_ends_when_the_user_is_removed(client, uow):
    login(client)
    uow.users._rows.pop(1)
    assert client.get("/api/auth/me").status_code == 401


def test_cookie_is_not_sent_over_plain_http(container):
    from fastapi.testclient import TestClient

    from safevision.adapters.inbound.http.app import create_app

    with TestClient(create_app(container)) as plain:  # http://testserver
        assert login(plain).status_code == 200
        assert plain.get("/api/auth/me").status_code == 401


def test_openapi_describes_the_session_route(client):
    operation = client.get("/openapi.json").json()["paths"]["/api/auth/me"]["get"]
    assert operation["summary"] == "Usuario actual de la sesión"


def test_logout_expires_the_cookie(client):
    login(client)
    response = client.post("/api/auth/logout", headers=PANEL)
    assert response.status_code == 204
    assert response.content == b""
    header = response.headers["set-cookie"]
    assert header.startswith(f'{SESSION_COOKIE}="";')
    assert "Max-Age=0" in header
    assert {"HttpOnly", "Secure", "Path=/", "SameSite=none"} <= {
        part.strip() for part in header.split(";")
    }
    assert client.get("/api/auth/me").status_code == 401


def test_logout_is_idempotent(client):
    assert client.post("/api/auth/logout").status_code == 204
    assert client.post("/api/auth/logout").status_code == 204


def test_openapi_describes_the_logout(client):
    operation = client.get("/openapi.json").json()["paths"]["/api/auth/logout"]["post"]
    assert operation["summary"] == "Cerrar sesión"
    assert "204" in operation["responses"]


def test_too_many_failures_answer_429(client):
    for _ in range(5):
        assert login(client, password="mala").status_code == 401
    response = login(client)
    assert response.status_code == 429
    assert response.json() == {
        "detail": "Demasiados intentos fallidos. Intenta de nuevo en unos minutos."
    }
    assert SESSION_COOKIE not in response.cookies


def test_logout_with_a_cookie_from_another_site_is_refused(client):
    login(client)
    response = client.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert response.status_code == 403
    assert response.json() == {"detail": "Origen no permitido"}
    assert client.get("/api/auth/me").status_code == 200
