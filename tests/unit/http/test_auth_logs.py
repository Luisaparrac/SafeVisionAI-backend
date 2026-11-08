"""What the account routes leave in the logs, and how OpenAPI documents them."""

import logging
from dataclasses import replace

import pytest

from tests.fakes.users import TEST_EMAIL

CODE = "codigo-invitacion-unico"
PASSWORD = "clave-registro-1"
NEW_PASSWORD = "clave-nueva-unica-2"
NEW_EMAIL = "eva.ruiz@example.com"
ADDRESS = "203.0.113.45"
EDGE = {"CF-Connecting-IP": ADDRESS}


@pytest.fixture
def settings(settings):
    return replace(settings, registration_mode="invite", registration_code=CODE)


def application_logs(caplog) -> str:
    return "\n".join(
        record.getMessage() + (record.exc_text or "")
        for record in caplog.records
        if record.name.startswith("safevision")
    )


def test_the_account_flows_log_no_sensitive_value(anonymous, outbox, caplog):
    body = {"name": "Eva Ruiz", "email": NEW_EMAIL, "password": PASSWORD}
    with caplog.at_level(logging.DEBUG):
        register = "/api/auth/register"
        anonymous.post(register, json=body | {"invitation_code": "otro-codigo"}, headers=EDGE)
        assert (
            anonymous.post(register, json=body | {"invitation_code": CODE}, headers=EDGE)
        ).status_code == 201
        anonymous.post("/api/auth/login", json={"email": NEW_EMAIL, "password": PASSWORD})
        forgot = anonymous.post(
            "/api/auth/password/forgot", json={"email": NEW_EMAIL}, headers=EDGE
        )
        assert forgot.status_code == 202
        token = outbox.sent[0].text.split("?token=")[1].split("\n")[0]
        anonymous.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": "corta"},
            headers=EDGE,
        )
        reset = anonymous.post(
            "/api/auth/password/reset",
            json={"token": token, "new_password": NEW_PASSWORD},
            headers=EDGE,
        )
        assert reset.status_code == 204
    logs = application_logs(caplog)
    assert "path=/api/auth/password/reset status=204" in logs  # the flow was logged
    for secret in (CODE, PASSWORD, NEW_PASSWORD, NEW_EMAIL, token, ADDRESS, "otro-codigo"):
        assert secret not in logs
    assert TEST_EMAIL not in logs


NEW_ROUTES = [
    ("post", "/api/auth/register", {"201", "403", "409", "422", "429"}),
    ("post", "/api/auth/password/forgot", {"202", "422", "429", "503"}),
    ("post", "/api/auth/password/reset", {"204", "400", "422", "429"}),
    ("get", "/api/auth/options", {"200"}),
]


@pytest.mark.parametrize(("method", "path", "codes"), NEW_ROUTES)
def test_openapi_documents_the_new_routes(anonymous, method, path, codes):
    operation = anonymous.get("/openapi.json").json()["paths"][path][method]
    assert operation["summary"]
    assert codes <= set(operation["responses"])


def test_new_routes_do_not_replace_the_ones_the_panel_finds_first(anonymous):
    # The panel takes the first auth routes of /openapi.json.
    paths = list(anonymous.get("/openapi.json").json()["paths"])
    auth_paths = [path for path in paths if path.startswith("/api/auth/")]
    assert auth_paths[:2] == ["/api/auth/login", "/api/auth/me"]
