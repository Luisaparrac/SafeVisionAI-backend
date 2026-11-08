import logging
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.bootstrap import build_container
from tests.fakes.users import FAST_HASHER, TEST_EMAIL

ACCEPTED = {
    "detail": "Si el correo está registrado, recibirás un enlace para restablecer la contraseña."
}


def forgot(client, email=TEST_EMAIL):
    return client.post("/api/auth/password/forgot", json={"email": email})


def test_registered_email_gets_the_link(anonymous, outbox):
    response = forgot(anonymous)
    assert (response.status_code, response.json()) == (202, ACCEPTED)
    assert [message.to for message in outbox.sent] == [TEST_EMAIL]
    assert "https://panel.example.com/restablecer?token=" in outbox.sent[0].text


@pytest.mark.parametrize("email", ["nadie@example.com", "no-es-correo", ""])
def test_unknown_email_gets_the_same_answer(anonymous, outbox, email):
    response = forgot(anonymous, email)
    assert (response.status_code, response.json()) == (202, ACCEPTED)
    assert outbox.sent == []


def test_the_answer_does_not_wait_for_the_user_lookup(anonymous, uow, monkeypatch):
    # Nothing of the users table is read before the task, which runs after the answer.
    order = []
    original = uow.users.find_by_email
    monkeypatch.setattr(
        uow.users, "find_by_email", lambda email: order.append("lookup") or original(email)
    )
    app = anonymous.app
    container = app.state.container
    monkeypatch.setattr(
        container.request_password_reset,
        "accept",
        lambda *args: order.append("accepted"),
    )
    forgot(anonymous)
    assert order == ["accepted", "lookup"]


def test_disabled_provider_answers_503(settings, uow, clock):
    container = build_container(settings, uow, clock, password_hasher=FAST_HASHER)
    with TestClient(create_app(container), base_url="https://testserver") as client:
        response = forgot(client)
    assert (response.status_code, response.json()) == (
        503,
        {"detail": "La recuperación de contraseña no está disponible"},
    )


@pytest.mark.parametrize("body", [{}, {"email": "a" * 321}, {"email": 5}])
def test_invalid_bodies(anonymous, body):
    assert anonymous.post("/api/auth/password/forgot", json=body).status_code == 422


def test_the_lifetime_comes_from_the_settings(settings, uow, clock, outbox):
    shorter = replace(settings, password_reset_ttl_minutes=5)
    container = build_container(
        shorter, uow, clock, password_hasher=FAST_HASHER, email_sender=outbox
    )
    with TestClient(create_app(container), base_url="https://testserver") as client:
        forgot(client)
    assert "5 minutos" in outbox.sent[0].text


def test_failures_after_the_answer_stay_out_of_the_response(anonymous, outbox, caplog, monkeypatch):
    def fail(_):
        raise OSError(f"sin red para {TEST_EMAIL}")

    monkeypatch.setattr(outbox, "send", fail)
    with caplog.at_level(logging.ERROR):
        assert forgot(anonymous).status_code == 202
    assert "OSError" in caplog.text
    assert TEST_EMAIL not in caplog.text


def test_openapi_describes_the_route(anonymous):
    operation = anonymous.get("/openapi.json").json()["paths"]["/api/auth/password/forgot"]["post"]
    assert operation["summary"] == "Solicitar enlace para restablecer la contraseña"
    assert {"202", "503"} <= set(operation["responses"])
