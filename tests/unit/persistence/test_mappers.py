"""ORM rows <-> domain entities, using transient rows (no database)."""

import ipaddress
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from safevision.adapters.outbound.persistence import mappers
from safevision.adapters.outbound.persistence.orm import (
    AlertRow,
    CameraRow,
    EventRow,
    EventTypeRow,
    LocationRow,
    SubjectRow,
    ZoneRow,
)
from safevision.domain.errors import ValidationError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import (
    AlertStatus,
    CameraStatus,
    Confidence,
    DetectedClass,
    EventStatus,
    Priority,
    Severity,
    SubjectType,
)

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def test_event_type_row_to_domain():
    row = EventTypeRow(
        event_type_id=3, name="Caída", description="Persona en el piso", severity_level=4
    )
    event_type = mappers.event_type_to_domain(row)
    assert event_type.id == 3
    assert event_type.name == "Caída"
    assert event_type.description == "Persona en el piso"
    assert event_type.severity == Severity(4)
    assert event_type.priority is Priority.HIGH


def test_event_type_with_invalid_severity_is_rejected():
    row = EventTypeRow(event_type_id=1, name="Raro", description=None, severity_level=9)
    with pytest.raises(ValidationError):
        mappers.event_type_to_domain(row)


def test_location_row_to_domain():
    row = LocationRow(location_id=2, name="Casa", description=None, user_id=5)
    location = mappers.location_to_domain(row)
    assert (location.id, location.name, location.description, location.user_id) == (
        2,
        "Casa",
        None,
        5,
    )


def test_subject_row_to_domain():
    row = SubjectRow(subject_id=7, name="Rosa", subject_type="elderly", description="", user_id=1)
    subject = mappers.subject_to_domain(row)
    assert subject.id == 7
    assert subject.subject_type is SubjectType.ELDERLY
    assert subject.description is None  # blank text is normalized by the domain


def camera_row(**overrides) -> CameraRow:
    values = {
        "camera_id": 1,
        "name": "Sala",
        "ip_address": "192.0.2.10",
        "status": "active",
        "location_id": 2,
    }
    return CameraRow(**(values | overrides))


def test_camera_row_to_domain():
    camera = mappers.camera_to_domain(camera_row(status="maintenance"))
    assert camera.id == 1
    assert camera.ip_address == ipaddress.ip_address("192.0.2.10")
    assert camera.status is CameraStatus.MAINTENANCE
    assert camera.location_id == 2


@pytest.mark.parametrize(
    "stored", ["192.0.2.10/32", ipaddress.ip_address("192.0.2.10"), " 192.0.2.10"]
)
def test_camera_ip_accepts_what_the_driver_returns(stored):
    camera = mappers.camera_to_domain(camera_row(ip_address=stored))
    assert camera.ip_address == ipaddress.ip_address("192.0.2.10")


def test_apply_camera_copies_the_changes_to_the_row():
    row = camera_row()
    camera = mappers.camera_to_domain(row)
    camera.change_status("disconnected")
    mappers.apply_camera(camera, row)
    assert row.status == "disconnected"
    assert row.ip_address == "192.0.2.10"
    assert row.camera_id == 1


def test_zone_row_to_domain():
    row = ZoneRow(
        zone_id=4,
        name="Escalera",
        description=None,
        coordinates=[[0, 0], [1, 0], [1, 1]],
        is_active=False,
        camera_id=1,
    )
    zone = mappers.zone_to_domain(row)
    assert zone.id == 4
    assert zone.polygon.to_list() == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0]]
    assert zone.is_active is False
    assert zone.belongs_to(1)


def test_zone_with_too_few_points_is_rejected():
    row = ZoneRow(zone_id=1, name="Mala", coordinates=[[0, 0]], is_active=True, camera_id=1)
    with pytest.raises(ValidationError):
        mappers.zone_to_domain(row)


def event_row(**overrides) -> EventRow:
    values = {
        "event_id": 9,
        "occurred_at": NOW,
        "description": "Caída en la sala",
        "status": "in_review",
        "detected_class": "dog",
        "confidence": Decimal("0.87"),
        "evidence_url": None,
        "subject_id": 3,
        "event_type_id": 1,
        "camera_id": 2,
        "zone_id": None,
    }
    return EventRow(**(values | overrides))


def test_event_row_to_domain():
    event = mappers.event_to_domain(event_row())
    assert event.id == 9
    assert event.occurred_at == NOW
    assert event.status is EventStatus.IN_REVIEW
    assert event.detected_class is DetectedClass.DOG
    assert event.confidence == Confidence(0.87)
    assert (event.subject_id, event.event_type_id, event.camera_id, event.zone_id) == (
        3,
        1,
        2,
        None,
    )


def test_event_without_confidence():
    assert mappers.event_to_domain(event_row(confidence=None)).confidence is None


def test_new_event_to_row_has_no_id():
    event = Event(camera_id=2, event_type_id=1, occurred_at=NOW, confidence=0.87, zone_id=5)
    row = mappers.event_to_row(event)
    assert row.event_id is None
    assert row.status == "pending"
    assert row.detected_class == "person"
    assert row.confidence == Decimal("0.87")
    assert row.zone_id == 5


def test_event_round_trip_keeps_every_field():
    row = event_row()
    copy = EventRow()
    mappers.apply_event(mappers.event_to_domain(row), copy)
    copy.event_id = row.event_id
    columns = [column.name for column in EventRow.__table__.columns]
    assert {c: getattr(copy, c) for c in columns} == {c: getattr(row, c) for c in columns}


def test_apply_event_stores_a_status_change():
    row = event_row(status="pending")
    event = mappers.event_to_domain(row)
    event.resolve()
    mappers.apply_event(event, row)
    assert row.status == "resolved"


def alert_row(**overrides) -> AlertRow:
    values = {
        "alert_id": 4,
        "created_at": NOW,
        "level": 3,
        "status": "active",
        "attended_at": None,
        "attended_by_user_id": None,
        "event_id": 9,
    }
    return AlertRow(**(values | overrides))


def test_alert_row_to_domain():
    alert = mappers.alert_to_domain(alert_row(status="seen"))
    assert alert.id == 4
    assert alert.level == Severity(3)
    assert alert.status is AlertStatus.SEEN
    assert alert.event_id == 9


def test_closed_alert_row_to_domain():
    attended = NOW + timedelta(minutes=5)
    alert = mappers.alert_to_domain(
        alert_row(status="resolved", attended_at=attended, attended_by_user_id=1)
    )
    assert alert.attended_at == attended
    assert alert.attended_by_user_id == 1


def test_new_alert_to_row_and_closing_it():
    alert = Alert(event_id=9, level=4, created_at=NOW)
    row = mappers.alert_to_row(alert)
    assert (row.alert_id, row.level, row.status, row.event_id) == (None, 4, "active", 9)
    alert.dismiss(NOW + timedelta(seconds=1))
    mappers.apply_alert(alert, row)
    assert row.status == "dismissed"
    assert row.attended_at == NOW + timedelta(seconds=1)
