import pytest

from safevision.adapters.inbound.http.sessions import SESSION, SESSION_COOKIE
from tests.fakes.users import TEST_EMAIL, TEST_NAME, TEST_PASSWORD

SESSION_BODY = {
    "authenticated": True,
    "user": {"id": 1, "name": TEST_NAME, "email": TEST_EMAIL},
}
WRONG = {"detail": "Correo o contraseña incorrectos"}


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
