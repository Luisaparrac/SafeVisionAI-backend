"""Harness of the HTTP contract tests.

The same tests run against every implementation of the API listed in
``BACKENDS``, all seeded with the same reference catalog (see
``tests.integration.postgres.insert_reference_rows``):

* ``hexagonal-memory``: the application with in-memory adapters;
* ``hexagonal-postgres``: the application with the SQLAlchemy adapters, as in
  production.

Until phase 8 they also ran against the previous application (app/), so the
expectations here are the behavior the frontend and the IoT module rely on.

Backends that need PostgreSQL are skipped without TEST_DATABASE_URL.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.bootstrap import build_container
from safevision.config.settings import Settings
from tests.fakes.catalog import seed_reference_catalog
from tests.fakes.unit_of_work import FakeUnitOfWork

KEY = {"X-API-Key": "test-key"}
EVENT_KEYS = {
    "id",
    "type",
    "subject",
    "location",
    "camera",
    "date",
    "time",
    "occurred_at",
    "priority",
    "status",
    "description",
}


SETTINGS = Settings(
    database_url="postgresql://test:test@localhost/test",
    iot_api_key="test-key",
    frontend_origins=("http://localhost:5173",),
    timezone="America/Bogota",
)


@contextmanager
def hexagonal_client(uow: UnitOfWork) -> Iterator[TestClient]:
    container = build_container(SETTINGS, uow, SystemClock())
    with TestClient(create_app(container)) as client:  # runs the startup rebuild
        yield client


@contextmanager
def hexagonal_memory_client(_: pytest.FixtureRequest) -> Iterator[TestClient]:
    uow = FakeUnitOfWork()
    seed_reference_catalog(uow)
    with hexagonal_client(uow) as client:
        yield client


@contextmanager
def hexagonal_postgres_client(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    engine = request.getfixturevalue("pg_seeded")
    with hexagonal_client(SqlAlchemyUnitOfWork(make_session_factory(engine))) as client:
        yield client


BACKENDS = {
    "hexagonal-memory": hexagonal_memory_client,
    "hexagonal-postgres": hexagonal_postgres_client,
}
NEEDS_DATABASE = {"hexagonal-postgres"}


@pytest.fixture(
    params=[
        pytest.param(name, marks=[pytest.mark.integration] if name in NEEDS_DATABASE else [])
        for name in BACKENDS
    ]
)
def client(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    with BACKENDS[request.param](request) as client:
        yield client


def post_event(client: TestClient, **body) -> dict:
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 201, response.text
    return response.json()
