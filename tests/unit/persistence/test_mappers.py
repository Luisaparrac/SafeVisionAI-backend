"""ORM rows <-> domain entities, using transient rows (no database)."""

import ipaddress

import pytest

from safevision.adapters.outbound.persistence import mappers
from safevision.adapters.outbound.persistence.orm import (
    CameraRow,
    EventTypeRow,
    LocationRow,
    SubjectRow,
    ZoneRow,
)
from safevision.domain.errors import ValidationError
from safevision.domain.model.values import CameraStatus, Priority, Severity, SubjectType


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
