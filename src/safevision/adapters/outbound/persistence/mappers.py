"""Translation between ORM rows and domain entities.

Rows never leave the persistence adapter: repositories return entities built
here, so the domain rules are checked on every read as well.
"""

from decimal import Decimal

from safevision.adapters.outbound.persistence.orm import (
    AlertRow,
    CameraRow,
    EventRow,
    EventTypeRow,
    LocationRow,
    SubjectRow,
    ZoneRow,
)
from safevision.domain.model.alert import Alert
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
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


def event_to_domain(row: EventRow) -> Event:
    return Event(
        id=row.event_id,
        occurred_at=row.occurred_at,
        description=row.description,
        status=row.status,
        detected_class=row.detected_class,
        confidence=None if row.confidence is None else float(row.confidence),
        evidence_url=row.evidence_url,
        subject_id=row.subject_id,
        event_type_id=row.event_type_id,
        camera_id=row.camera_id,
        zone_id=row.zone_id,
    )


def event_to_row(event: Event) -> EventRow:
    """New row for an event not stored yet; the database assigns its id."""
    row = EventRow()
    apply_event(event, row)
    return row


def apply_event(event: Event, row: EventRow) -> None:
    row.occurred_at = event.occurred_at
    row.description = event.description
    row.status = event.status.value
    row.detected_class = event.detected_class.value
    # Through text, so 0.87 is stored as 0.87 and not as its binary approximation.
    row.confidence = None if event.confidence is None else Decimal(str(event.confidence.value))
    row.evidence_url = event.evidence_url
    row.subject_id = event.subject_id
    row.event_type_id = event.event_type_id
    row.camera_id = event.camera_id
    row.zone_id = event.zone_id


def alert_to_domain(row: AlertRow) -> Alert:
    return Alert(
        id=row.alert_id,
        created_at=row.created_at,
        level=row.level,
        status=row.status,
        attended_at=row.attended_at,
        attended_by_user_id=row.attended_by_user_id,
        event_id=row.event_id,
    )


def alert_to_row(alert: Alert) -> AlertRow:
    """New row for an alert not stored yet; the database assigns its id."""
    row = AlertRow()
    apply_alert(alert, row)
    return row


def apply_alert(alert: Alert, row: AlertRow) -> None:
    row.created_at = alert.created_at
    row.level = alert.level.level
    row.status = alert.status.value
    row.attended_at = alert.attended_at
    row.attended_by_user_id = alert.attended_by_user_id
    row.event_id = alert.event_id
