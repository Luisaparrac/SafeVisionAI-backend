"""Smoke tests: the current application imports and answers without a database."""

from fastapi.testclient import TestClient


def test_app_imports_with_fake_environment():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/api/eventos" in paths


def test_health_responds_without_running_lifespan():
    from app.main import app

    # Not used as a context manager, so the lifespan (database access) never runs.
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
