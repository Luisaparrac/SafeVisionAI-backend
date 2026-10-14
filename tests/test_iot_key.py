"""X-API-Key protection of the IoT endpoints (no database involved)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong-key"}, {"X-API-Key": ""}])
def test_camera_status_rejects_missing_or_wrong_key(headers):
    response = client.patch("/api/camaras/1/estado", json={"status": "active"}, headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "X-API-Key inválida"}


def test_create_event_rejects_wrong_key():
    response = client.post(
        "/api/eventos",
        json={"camera_id": 1, "event_type": "Caída"},
        headers={"X-API-Key": "test-key-but-longer"},
    )
    assert response.status_code == 401


def test_non_ascii_key_is_rejected_without_error():
    response = client.patch(
        "/api/camaras/1/estado",
        json={"status": "active"},
        headers={"X-API-Key": "clave-ñ".encode()},
    )
    assert response.status_code == 401
