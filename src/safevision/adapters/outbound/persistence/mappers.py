"""Translation between ORM rows and domain entities.

Rows never leave the persistence adapter: repositories return entities built
here, so the domain rules are checked on every read as well.
"""

from safevision.adapters.outbound.persistence.orm import (
    CameraRow,
    EventTypeRow,
    LocationRow,
    SubjectRow,
    ZoneRow,
)
from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone


def event_type_to_domain(row: EventTypeRow) -> EventType:
    return EventType(
        id=row.event_type_id,
        name=row.name,
        description=row.description,
        severity=row.severity_level,
    )


def location_to_domain(row: LocationRow) -> Location:
    return Location(
        id=row.location_id,
        name=row.name,
        description=row.description,
        user_id=row.user_id,
    )


def subject_to_domain(row: SubjectRow) -> Subject:
    return Subject(
        id=row.subject_id,
        name=row.name,
        subject_type=row.subject_type,
        description=row.description,
        user_id=row.user_id,
    )


def camera_to_domain(row: CameraRow) -> Camera:
    return Camera(
        id=row.camera_id,
        name=row.name,
        ip_address=_host_address(row.ip_address),
        status=row.status,
        location_id=row.location_id,
    )


def apply_camera(camera: Camera, row: CameraRow) -> None:
    """Copies the editable fields of the entity onto its stored row."""
    row.name = camera.name
    row.ip_address = str(camera.ip_address)
    row.status = camera.status.value
    row.location_id = camera.location_id


def _host_address(value: object) -> str:
    # PostgreSQL may return an inet value with a prefix ("192.0.2.1/32").
    return str(value).split("/", 1)[0]


def zone_to_domain(row: ZoneRow) -> Zone:
    return Zone(
        id=row.zone_id,
        name=row.name,
        description=row.description,
        polygon=row.coordinates,
        is_active=row.is_active,
        camera_id=row.camera_id,
    )
