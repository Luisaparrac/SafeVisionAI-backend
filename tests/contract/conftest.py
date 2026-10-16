"""Harness of the HTTP contract tests.

The same tests run against every implementation of the API listed in
``BACKENDS``, all seeded with the same reference catalog (see
``tests.integration.postgres.insert_reference_rows``):

* ``legacy``: the application in app/, currently in production;
* ``hexagonal-memory``: the new application with in-memory adapters;
* ``hexagonal-postgres``: the new application with the SQLAlchemy adapters.

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
    "priority",
    "status",
    "description",
}


@contextmanager
def legacy_client(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    """The application in app/, currently in production, on the test database."""
    from app import services
    from app.database import get_db
    from app.main import app

    engine = request.getfixturevalue("pg_seeded")
    session_factory = make_session_factory(engine)

    def test_db():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = test_db
    with session_factory() as db:
        services.rebuild_structures(db)
    try:
        # Not used as a context manager: its lifespan would open the production URL.
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


# Same values the legacy application reads from the environment in tests/conftest.py.
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
    "legacy": legacy_client,
    "hexagonal-memory": hexagonal_memory_client,
    "hexagonal-postgres": hexagonal_postgres_client,
}
NEEDS_DATABASE = {"legacy", "hexagonal-postgres"}


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
