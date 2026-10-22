"""An HTTP client on the new application with in-memory adapters."""

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.bootstrap import build_container
from safevision.config.settings import Settings
from tests.fakes.catalog import seed_reference_catalog
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql://test:test@localhost/test",
        iot_api_key="test-key",
        session_secret="test-session-secret-0123456789abcdef",
        frontend_origins=("http://localhost:5173",),
    )


@pytest.fixture
def uow() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    seed_reference_catalog(uow)
    return uow


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def container(settings, uow, clock):
    return build_container(settings, uow, clock)


@pytest.fixture
def client(container):
    with TestClient(create_app(container)) as client:  # runs the lifespan
        yield client
