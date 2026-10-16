import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.security import require_iot_key


@pytest.fixture
def protected(container) -> TestClient:
    app = FastAPI()
    app.state.container = container

    @app.post("/protegido", dependencies=[Depends(require_iot_key)])
    def protegido() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_the_configured_key_is_accepted(protected):
    response = protected.post("/protegido", headers={"X-API-Key": "test-key"})
    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"X-API-Key": ""},
        {"X-API-Key": "wrong-key"},
        {"X-API-Key": "test-key-but-longer"},
        {"X-API-Key": "TEST-KEY"},
        {"X-API-Key": "clave-ñ".encode()},
    ],
)
def test_anything_else_is_rejected(protected, headers):
    response = protected.post("/protegido", headers=headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "X-API-Key inválida"}


def test_comparison_takes_constant_time(monkeypatch):
    import safevision.adapters.inbound.http.security as security

    calls = []
    original = security.hmac.compare_digest
    monkeypatch.setattr(
        security.hmac, "compare_digest", lambda a, b: calls.append((a, b)) or original(a, b)
    )

    class Holder:
        iot_api_key = "test-key"

    security.require_iot_key("test-key", Holder())
    assert calls == [(b"test-key", b"test-key")]
