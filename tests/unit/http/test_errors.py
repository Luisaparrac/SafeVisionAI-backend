import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.errors import install_error_handlers, status_for
from safevision.domain.errors import (
    DomainError,
    InvalidTransitionError,
    NotFoundError,
    ValidationError,
)

ERRORS = {
    "not-found": NotFoundError("Evento", 9),
    "transition": InvalidTransitionError("Evento", "resolved", "in_review"),
    "validation": ValidationError("Envía event_type_id o event_type"),
    "other": DomainError("Regla incumplida"),
}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/falla/{kind}")
    def fail(kind: str) -> None:
        raise ERRORS[kind]

    return TestClient(app)


@pytest.mark.parametrize(
    ("kind", "status", "detail"),
    [
        ("not-found", 404, "Evento 9 no existe"),
        ("transition", 409, "Evento: no se puede pasar de 'resolved' a 'in_review'"),
        ("validation", 422, "Envía event_type_id o event_type"),
        ("other", 400, "Regla incumplida"),
    ],
)
def test_domain_errors_become_http_errors(client, kind, status, detail):
    response = client.get(f"/falla/{kind}")
    assert response.status_code == status
    assert response.json() == {"detail": detail}


def test_subclasses_use_the_status_of_their_parent():
    class MissingCamera(NotFoundError):
        pass

    assert status_for(MissingCamera("Cámara", 1)) == 404
