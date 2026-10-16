"""Harness of the HTTP contract tests.

The same tests run against every implementation of the API listed in
``BACKENDS``, all seeded with the same reference catalog (see
``tests.integration.postgres.insert_reference_rows``). Backends that need
PostgreSQL are skipped without TEST_DATABASE_URL.
"""

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.outbound.persistence.database import make_session_factory

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


BACKENDS = {"legacy": legacy_client}


@pytest.fixture(params=sorted(BACKENDS))
def client(request: pytest.FixtureRequest) -> Iterator[TestClient]:
    with BACKENDS[request.param](request) as client:
        yield client


def post_event(client: TestClient, **body) -> dict:
    response = client.post("/api/eventos", json=body, headers=KEY)
    assert response.status_code == 201, response.text
    return response.json()
