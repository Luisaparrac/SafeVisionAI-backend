from dataclasses import replace

import pytest

from safevision.adapters.inbound.http.sessions import SESSION_COOKIE
from tests.fakes.users import TEST_EMAIL

CODE = "código-de-prueba"
BODY = {
    "name": "Eva Ruiz",
    "email": "Eva@Example.com",
    "password": "clave123",
    "invitation_code": CODE,
}
CREATED = {
    "authenticated": True,
    "user": {"id": 2, "name": "Eva Ruiz", "email": "eva@example.com"},
}


@pytest.fixture
def settings(settings):
    return replace(settings, registration_mode="invite", registration_code=CODE)


def register(client, **changes):
    return client.post("/api/auth/register", json=BODY | changes)


def test_register_creates_the_account_and_opens_the_session(anonymous):
    response = register(anonymous)
    assert response.status_code == 201
    assert response.json() == CREATED
    assert "HttpOnly" in response.headers["set-cookie"]
    assert anonymous.get("/api/auth/me").json() == CREATED


def test_the_new_account_can_log_in(anonymous):
    register(anonymous)
    credentials = {"email": "eva@example.com", "password": "clave123"}
    response = anonymous.post("/api/auth/login", json=credentials)
    assert (response.status_code, response.json()) == (200, CREATED)


@pytest.mark.parametrize("code", ["otro", "", None])
def test_wrong_code(anonymous, code):
    response = register(anonymous, invitation_code=code)
    assert (response.status_code, response.json()) == (
        403,
        {"detail": "Código de invitación inválido"},
    )
    assert SESSION_COOKIE not in response.cookies


def test_missing_code(anonymous):
    body = {k: v for k, v in BODY.items() if k != "invitation_code"}
    assert anonymous.post("/api/auth/register", json=body).status_code == 403


def test_existing_email(anonymous):
    response = register(anonymous, email=TEST_EMAIL.upper())
    assert (response.status_code, response.json()) == (
        409,
        {"detail": "Ya existe una cuenta con ese correo"},
    )


@pytest.mark.parametrize(
    ("change", "detail"),
    [
        ({"password": "corta1"}, "La contraseña debe tener al menos 8 caracteres"),
        ({"password": "x1" * 65}, "La contraseña no puede superar 128 caracteres"),
        ({"password": "sinnumeros"}, "La contraseña debe incluir al menos una letra y un número"),
        ({"name": " Eva"}, "El nombre no puede empezar ni terminar con espacios"),
        ({"name": "E"}, "El nombre debe tener entre 2 y 100 caracteres"),
        ({"email": "no-es-correo"}, "El correo no tiene un formato válido"),
    ],
)
def test_policy_messages(anonymous, change, detail):
    response = register(anonymous, **change)
    assert (response.status_code, response.json()) == (422, {"detail": detail})


@pytest.mark.parametrize("missing", ["name", "email", "password"])
def test_required_fields(anonymous, missing):
    body = {k: v for k, v in BODY.items() if k != missing}
    response = anonymous.post("/api/auth/register", json=body)
    assert response.status_code == 422


def test_openapi_describes_the_route(anonymous):
    operation = anonymous.get("/openapi.json").json()["paths"]["/api/auth/register"]["post"]
    assert operation["summary"] == "Crear cuenta"
    assert {"201", "403", "409", "422"} <= set(operation["responses"])


def app_with(settings, uow, clock):
    from fastapi.testclient import TestClient

    from safevision.adapters.inbound.http.app import create_app
    from safevision.bootstrap import build_container
    from tests.fakes.users import FAST_HASHER

    container = build_container(settings, uow, clock, password_hasher=FAST_HASHER)
    return TestClient(create_app(container), base_url="https://testserver")


CLOSED = {"detail": "El registro de cuentas no está habilitado"}


def test_closed_mode(settings, uow, clock):
    closed = replace(settings, registration_mode="closed")
    with app_with(closed, uow, clock) as client:
        response = register(client)
    assert (response.status_code, response.json()) == (403, CLOSED)


def test_invite_mode_without_a_configured_code_is_closed(settings, uow, clock):
    without_code = replace(settings, registration_code="")
    with app_with(without_code, uow, clock) as client:
        response = register(client, invitation_code="")
    assert (response.status_code, response.json()) == (403, CLOSED)


def test_open_mode_needs_no_code(settings, uow, clock):
    open_mode = replace(settings, registration_mode="open", registration_code="")
    with app_with(open_mode, uow, clock) as client:
        response = client.post(
            "/api/auth/register",
            json={"name": "Eva Ruiz", "email": "eva@example.com", "password": "clave123"},
        )
    assert response.status_code == 201


def test_six_attempts_from_one_address_answer_429(anonymous):
    for _ in range(5):
        assert register(anonymous, invitation_code="mal").status_code == 403
    response = register(anonymous)
    assert (response.status_code, response.json()) == (
        429,
        {"detail": "Demasiadas solicitudes. Intenta de nuevo más tarde."},
    )


def test_the_limit_ends_after_an_hour(anonymous, clock):
    for _ in range(5):
        register(anonymous, invitation_code="mal")
    assert register(anonymous).status_code == 429
    clock.advance(3600)
    assert register(anonymous).status_code == 201


def test_the_limit_counts_the_edge_address_not_the_fake_list(anonymous):
    def attempt(**headers):
        return anonymous.post(
            "/api/auth/register", json=BODY | {"invitation_code": "mal"}, headers=headers
        ).status_code

    edge = {"CF-Connecting-IP": "203.0.113.5"}
    for fake in range(5):
        assert attempt(**edge, **{"X-Forwarded-For": f"198.51.100.{fake}"}) == 403
    assert attempt(**edge, **{"X-Forwarded-For": "198.51.100.77"}) == 429
    assert attempt(**{"CF-Connecting-IP": "203.0.113.6"}) == 403
