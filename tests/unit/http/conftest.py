"""HTTP clients on the application with in-memory adapters.

``client`` is the panel: logged in as the test user and sending the Origin of
the frontend. ``anonymous`` is the same browser before logging in.
"""

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.bootstrap import build_container
from safevision.config.settings import Settings
from tests.fakes.catalog import seed_reference_catalog
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork
from tests.fakes.users import FAST_HASHER, TEST_EMAIL, TEST_PASSWORD

PANEL_ORIGIN = "http://localhost:5173"


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
    return build_container(settings, uow, clock, password_hasher=FAST_HASHER)


@pytest.fixture
def anonymous(container):
    # https: the session cookie is Secure, so the client only sends it back over https.
    app = create_app(container)
    headers = {"Origin": PANEL_ORIGIN}
    with TestClient(app, base_url="https://testserver", headers=headers) as client:  # lifespan
        yield client


def log_in(client: TestClient) -> TestClient:
    """Opens a session as the test user; again after the clock passes SESSION_TTL_HOURS."""
    credentials = {"email": TEST_EMAIL, "password": TEST_PASSWORD}
    assert client.post("/api/auth/login", json=credentials).status_code == 200
    return client


@pytest.fixture
def client(anonymous):
    return log_in(anonymous)
