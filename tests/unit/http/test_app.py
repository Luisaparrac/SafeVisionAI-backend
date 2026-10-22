from fastapi.testclient import TestClient

from safevision.adapters.inbound.http.app import create_app
from safevision.application.use_cases.register_event import RegisterEventCommand
from safevision.bootstrap import build_container


def test_root_and_health(client):
    assert client.get("/").json() == {"servicio": "SafeVision AI backend", "docs": "/docs"}
    assert client.get("/health").json() == {"status": "ok"}


def test_cors_uses_the_configured_origins(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_openapi_metadata(client):
    info = client.get("/openapi.json").json()["info"]
    assert info["title"] == "SafeVision AI - Backend"
    assert "IoT" in info["description"]


def test_startup_rebuilds_the_board_from_the_database(settings, uow, clock):
    # Events stored by a previous run of the application...
    previous = build_container(settings, uow, clock)
    previous.register_event.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    # ...are pending again after a restart.
    container = build_container(settings, uow, clock)
    assert container.get_metrics.execute().pending == 0
    with TestClient(create_app(container)):
        assert container.get_metrics.execute().pending == 1


def test_domain_errors_are_translated(container):
    app = create_app(container)

    @app.get("/prueba-error")
    def fail() -> None:
        container.get_event.execute(999)

    response = TestClient(app).get("/prueba-error")
    assert response.status_code == 404
    assert response.json() == {"detail": "Evento 999 no existe"}


def test_openapi_has_examples_for_the_iot_requests(client):
    from safevision.adapters.inbound.http.schemas import CameraStatusIn, EventIn

    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    event_examples = schemas["EventIn"]["examples"]
    status_examples = schemas["CameraStatusIn"]["examples"]
    # Names of the real catalog (event_types), not translations.
    assert event_examples[0]["event_type"] == "Fall"
    assert status_examples == [{"status": "disconnected"}]
    # The examples are valid requests.
    for example in event_examples:
        EventIn.model_validate(example)
    for example in status_examples:
        CameraStatusIn.model_validate(example)
