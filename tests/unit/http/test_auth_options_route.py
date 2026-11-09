from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.bootstrap import build_container
from tests.fakes.email import CapturingEmailSender
from tests.fakes.users import FAST_HASHER


def options(settings, uow, clock, sender=None):
    container = build_container(
        settings, uow, clock, password_hasher=FAST_HASHER, email_sender=sender
    )
    with TestClient(create_app(container), base_url="https://testserver") as client:
        response = client.get("/api/auth/options")
    assert response.status_code == 200
    return response.json()


@pytest.mark.parametrize(
    ("mode", "code", "expected"),
    [
        ("closed", "", "closed"),
        ("closed", "abc", "closed"),
        ("open", "", "open"),
        ("invite", "abc", "invite"),
        ("invite", "", "closed"),  # without a code nobody could register
    ],
)
def test_registration_mode(settings, uow, clock, mode, code, expected):
    changed = replace(settings, registration_mode=mode, registration_code=code)
    assert options(changed, uow, clock)["registration"] == expected


def test_password_recovery_follows_the_sender(settings, uow, clock):
    assert options(settings, uow, clock)["password_recovery"] is False
    assert options(settings, uow, clock, CapturingEmailSender())["password_recovery"] is True


def test_the_code_is_never_returned(settings, uow, clock):
    changed = replace(settings, registration_mode="invite", registration_code="super-secreto")
    assert options(changed, uow, clock) == {"registration": "invite", "password_recovery": False}


def test_openapi_describes_the_route(anonymous):
    operation = anonymous.get("/openapi.json").json()["paths"]["/api/auth/options"]["get"]
    assert operation["summary"] == "Opciones de autenticación disponibles"
