"""A database that cannot be reached gives a 503 without internal details."""

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.adapters.outbound.persistence.database import make_engine, make_session_factory
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.bootstrap import build_container
from safevision.config.settings import Settings

pytestmark = pytest.mark.integration


def test_unreachable_database_answers_503(pg_engine):
    # A port where nothing listens: every query fails to connect.
    url = pg_engine.url.set(port=1, query={"connect_timeout": "2"})
    engine = make_engine(url.render_as_string(hide_password=False))
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        iot_api_key="k",
        session_secret="test-session-secret-0123456789abcdef",
    )
    uow = SqlAlchemyUnitOfWork(make_session_factory(engine))
    client = TestClient(create_app(build_container(settings, uow, SystemClock())))
    # Without the startup rebuild, which would fail; the key needs no database.
    response = client.get("/api/eventos", headers={"X-API-Key": "k"})
    assert response.status_code == 503
    assert response.json() == {
        "detail": "La base de datos no está disponible. Intenta de nuevo más tarde."
    }
    engine.dispose()
