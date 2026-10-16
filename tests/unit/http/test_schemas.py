import pytest
from pydantic import ValidationError

from safevision.adapters.inbound.http import schemas
from safevision.application.dto import AlertView, EventView, Metrics
from safevision.application.use_cases.register_event import RegisterEventCommand
from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone

VIEW = EventView(
    id=7,
    type="Caída",
    subject="Rosa",
    location="Casa · Escalera",
    camera="Sala",
    date="2026-10-15",
    time="07:00:00",
    priority="Alto",
    status="Pendiente",
    description=None,
)
VIEW_JSON = {
    "id": 7,
    "type": "Caída",
    "subject": "Rosa",
    "location": "Casa · Escalera",
    "camera": "Sala",
    "date": "2026-10-15",
    "time": "07:00:00",
    "priority": "Alto",
    "status": "Pendiente",
    "description": None,
}


def test_event_view_keeps_the_contract_keys():
    assert schemas.EventOut.from_view(VIEW).model_dump() == VIEW_JSON


def test_alert_view_uses_the_spanish_keys():
    alert = AlertView(alert_id=3, level="Alto", status="Activa", event=VIEW)
    assert schemas.AlertOut.from_view(alert).model_dump() == {
        "id_alerta": 3,
        "nivel": "Alto",
        "estado": "Activa",
        "event": VIEW_JSON,
    }


def test_metrics_use_the_spanish_keys():
    metrics = schemas.MetricsOut.from_metrics(Metrics(total=5, pending=2, high=1))
    assert metrics.model_dump() == {"total": 5, "pendientes": 2, "alto": 1}


def test_event_in_defaults_and_command():
    body = schemas.EventIn.model_validate({"camera_id": 1, "event_type": "Caída"})
    assert body.to_command() == RegisterEventCommand(camera_id=1, event_type="Caída")


def test_event_in_ignores_unknown_fields():
    body = schemas.EventIn.model_validate({"camera_id": 1, "event_type_id": 2, "extra": True})
    assert body.to_command().event_type_id == 2


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"camera_id": 1, "confidence": -0.1},
        {"camera_id": 1, "confidence": 1.01},
        {"camera_id": 1, "detected_class": "robot"},
    ],
)
def test_event_in_validation(body):
    with pytest.raises(ValidationError):
        schemas.EventIn.model_validate(body)


def test_camera_status_in_accepts_only_known_statuses():
    assert schemas.CameraStatusIn(status="maintenance").status == "maintenance"
    with pytest.raises(ValidationError):
        schemas.CameraStatusIn(status="broken")


def test_camera_outputs():
    camera = Camera(id=1, name="Sala", ip_address="192.0.2.1", location_id=2, status="inactive")
    assert schemas.CameraOut.from_entity(camera).model_dump() == {
        "camera_id": 1,
        "name": "Sala",
        "ip_address": "192.0.2.1",
        "status": "inactive",
        "location_id": 2,
    }
    assert schemas.CameraStatusOut.from_entity(camera).model_dump() == {
        "camera_id": 1,
        "status": "inactive",
    }


def test_catalog_outputs():
    event_type = EventType(id=4, name="Humo", severity=3)
    assert schemas.EventTypeOut.from_entity(event_type).model_dump() == {
        "event_type_id": 4,
        "name": "Humo",
        "description": None,
        "severity_level": 3,
        "priority": "Alto",
    }
    location = Location(id=1, name="Casa", user_id=1, description="Principal")
    assert schemas.LocationOut.from_entity(location).model_dump() == {
        "location_id": 1,
        "name": "Casa",
        "description": "Principal",
    }
    subject = Subject(id=1, name="Rosa", subject_type="elderly", user_id=1)
    assert schemas.SubjectOut.from_entity(subject).model_dump() == {
        "subject_id": 1,
        "name": "Rosa",
        "subject_type": "elderly",
        "description": None,
    }
    zone = Zone(id=2, name="Puerta", camera_id=1, polygon=[[0, 0], [1, 0], [1, 1]])
    assert schemas.ZoneOut.from_entity(zone).model_dump() == {
        "zone_id": 2,
        "name": "Puerta",
        "description": None,
        "coordinates": [[0, 0], [1, 0], [1, 1]],
        "is_active": True,
        "camera_id": 1,
    }
