"""The development sample data loads on top of schema.sql and the application reads it."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.bootstrap import build_container
from safevision.config.settings import Settings
from tests.integration.postgres import sql_statements

pytestmark = pytest.mark.integration

SEED = Path(__file__).resolve().parents[2] / "scripts" / "seed_dev.sql"


@pytest.fixture
def client(pg_clean):
    with pg_clean.begin() as connection:
        for statement in sql_statements(SEED):
            connection.exec_driver_sql(statement)
    settings = Settings(
        database_url="postgresql://test:test@localhost/test",
        iot_api_key="k",
        session_secret="test-session-secret-0123456789abcdef",
    )
    uow = SqlAlchemyUnitOfWork(make_session_factory(pg_clean))
    app = create_app(build_container(settings, uow, SystemClock()))
    # The sample user has no valid password hash; the IoT key also reads the panel routes.
    with TestClient(app, headers={"X-API-Key": "k"}) as client:
        yield client


def test_sample_data_is_valid_for_the_domain(client):
    events = client.get("/api/eventos").json()
    assert [e["type"] for e in events] == ["Caída", "Humo", "Merodeo", "Ruido"]
    assert [e["status"] for e in events] == ["Pendiente", "Pendiente", "Revisado", "Revisado"]
    assert events[0]["location"] == "Casa de ejemplo · Escalera"
    assert events[0]["subject"] == "Rosa"


def test_open_alerts_are_pending_after_startup(client):
    alerts = client.get("/api/alertas/pendientes").json()
    assert [(a["nivel"], a["event"]["type"]) for a in alerts] == [
        ("Alto", "Caída"),
        ("Alto", "Humo"),
    ]
    assert client.get("/api/metricas").json() == {"total": 4, "pendientes": 2, "alto": 2}


def test_catalogs(client):
    cameras = client.get("/api/camaras").json()
    assert [(c["name"], c["status"]) for c in cameras] == [
        ("Sala", "active"),
        ("Patio", "active"),
        ("Cocina", "maintenance"),
    ]
    assert all(c["ip_address"].startswith("192.0.2.") for c in cameras)
    assert len(client.get("/api/sujetos").json()) == 2
