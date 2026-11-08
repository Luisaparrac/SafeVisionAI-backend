import pytest

from safevision.adapters.inbound.http.sessions import SESSION_COOKIE, WS_TICKET, WS_TICKET_LIFETIME
from tests.fakes.users import TEST_EMAIL, TEST_FINGERPRINT, TEST_PASSWORD

NEW = "clave-nueva-1"
BAD_LINK = {"detail": "El enlace no es válido o expiró"}


def reset(client, token, password=NEW):
    return client.post("/api/auth/password/reset", json={"token": token, "new_password": password})


def login(client, password):
    return client.post("/api/auth/login", json={"email": TEST_EMAIL, "password": password})


@pytest.fixture
def token(anonymous, outbox) -> str:
    assert (
        anonymous.post("/api/auth/password/forgot", json={"email": TEST_EMAIL}).status_code == 202
    )
    return outbox.sent[-1].text.split("?token=")[1].split("\n")[0]


def test_reset_changes_the_password_without_logging_in(anonymous, token):
    response = reset(anonymous, token)
    assert response.status_code == 204
    assert response.content == b""
    assert "set-cookie" not in response.headers
    assert anonymous.get("/api/auth/me").status_code == 401
    assert login(anonymous, TEST_PASSWORD).status_code == 401
    assert login(anonymous, NEW).status_code == 200


def test_reset_ends_the_previous_sessions(anonymous, token):
    assert login(anonymous, TEST_PASSWORD).status_code == 200
    assert anonymous.get("/api/auth/me").status_code == 200
    assert reset(anonymous, token).status_code == 204
    assert anonymous.get("/api/auth/me").status_code == 401


def test_the_link_cannot_be_used_twice(anonymous, token):
    assert reset(anonymous, token).status_code == 204
    response = reset(anonymous, token, "otra-clave-2")
    assert (response.status_code, response.json()) == (400, BAD_LINK)


def test_expired_link(anonymous, token, clock):
    clock.advance(30 * 60)
    response = reset(anonymous, token)
    assert (response.status_code, response.json()) == (400, BAD_LINK)


@pytest.mark.parametrize(
    ("password", "detail"),
    [
        ("corta1", "La contraseña debe tener al menos 8 caracteres"),
        ("x1" * 65, "La contraseña no puede superar 128 caracteres"),
        ("sin-numeros", "La contraseña debe incluir al menos una letra y un número"),
    ],
)
def test_policy_messages(anonymous, token, password, detail):
    response = reset(anonymous, token, password)
    assert (response.status_code, response.json()) == (422, {"detail": detail})
    assert reset(anonymous, token).status_code == 204  # the link was not spent


@pytest.mark.parametrize("bad", ["", "basura", "a.b", "ñ.ñ"])
def test_invalid_links(anonymous, bad):
    response = reset(anonymous, bad)
    assert (response.status_code, response.json()) == (400, BAD_LINK)


def test_a_token_with_broken_unicode_is_an_invalid_link(anonymous):
    body = b'{"token": "a.\ud800", "new_password": "clave-nueva-1"}'
    headers = {"Content-Type": "application/json"}
    response = anonymous.post("/api/auth/password/reset", content=body, headers=headers)
    assert (response.status_code, response.json()) == (400, BAD_LINK)


def test_a_session_or_a_ticket_is_not_a_link(anonymous, container):
    signer = container.sessions.signer
    assert login(anonymous, TEST_PASSWORD).status_code == 200
    cookie = anonymous.cookies[SESSION_COOKIE]
    ticket = signer.issue(1, WS_TICKET, WS_TICKET_LIFETIME, TEST_FINGERPRINT)
    assert reset(anonymous, cookie).status_code == 400
    assert reset(anonymous, ticket).status_code == 400


def test_a_link_is_neither_a_session_nor_a_ticket(anonymous, token):
    anonymous.cookies.set(SESSION_COOKIE, token)
    assert anonymous.get("/api/auth/me").status_code == 401
    with anonymous.websocket_connect(f"/ws/alertas?ticket={token}") as feed:
        assert feed.receive()["code"] == 4401


def test_eleventh_attempt_from_one_address_answers_429(anonymous):
    for _ in range(10):
        assert reset(anonymous, "basura").status_code == 400
    response = reset(anonymous, "basura")
    assert (response.status_code, response.json()) == (
        429,
        {"detail": "Demasiadas solicitudes. Intenta de nuevo más tarde."},
    )


@pytest.mark.parametrize("body", [{}, {"token": "x"}, {"new_password": "x"}, {"token": 5}])
def test_invalid_bodies(anonymous, body):
    assert anonymous.post("/api/auth/password/reset", json=body).status_code == 422


def test_openapi_describes_the_route(anonymous):
    operation = anonymous.get("/openapi.json").json()["paths"]["/api/auth/password/reset"]["post"]
    assert operation["summary"] == "Restablecer la contraseña"
    assert {"204", "400", "422", "429"} <= set(operation["responses"])
