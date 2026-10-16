from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.adapters.outbound.persistence.database import make_engine
from safevision.adapters.outbound.persistence.readiness import DatabaseReadinessProbe
from safevision.application.ports.readiness import ReadinessProbe
from safevision.bootstrap import AlwaysReady, build_container


class NotReady:
    def is_ready(self) -> bool:
        return False


def test_ready_when_the_probe_succeeds(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_not_ready_when_the_database_fails(settings, uow, clock):
    container = build_container(settings, uow, clock, NotReady())
    client = TestClient(create_app(container))  # no lifespan: the database is down
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "database": "error"}
    # Liveness does not depend on the database.
    assert client.get("/health").json() == {"status": "ok"}


def test_probes_satisfy_the_port():
    assert isinstance(AlwaysReady(), ReadinessProbe)
    assert isinstance(
        DatabaseReadinessProbe(make_engine("postgresql://t:t@localhost/t")), ReadinessProbe
    )


def test_unreachable_database_is_not_ready_and_does_not_raise(caplog):
    engine = make_engine("postgresql://test:secret@127.0.0.1:1/nothing_test?connect_timeout=2")
    assert DatabaseReadinessProbe(engine).is_ready() is False
    assert "secret" not in caplog.text
    engine.dispose()
