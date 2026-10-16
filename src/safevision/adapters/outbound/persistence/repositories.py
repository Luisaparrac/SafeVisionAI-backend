"""SQLAlchemy implementations of the repository ports.

Each repository works on the session of the current unit of work: it flushes
its changes so ids and constraints are checked at once, but never commits.
"""

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

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
from safevision.application.ports.repositories import EventFilter
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone


class SqlAlchemyEventTypeRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_type_id: int) -> EventType | None:
        row = self._session.get(EventTypeRow, event_type_id)
        return None if row is None else mappers.event_type_to_domain(row)

    def find_by_name(self, name: str) -> EventType | None:
        row = self._session.scalars(
            select(EventTypeRow)
            .where(func.lower(EventTypeRow.name) == name.strip().lower())
            .order_by(EventTypeRow.event_type_id)
            .limit(1)
        ).first()
        return None if row is None else mappers.event_type_to_domain(row)

    def list_all(self) -> list[EventType]:
        rows = self._session.scalars(
            select(EventTypeRow).order_by(EventTypeRow.severity_level.desc(), EventTypeRow.name)
        )
        return [mappers.event_type_to_domain(row) for row in rows]


class SqlAlchemyCatalogRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_location(self, location_id: int) -> Location | None:
        row = self._session.get(LocationRow, location_id)
        return None if row is None else mappers.location_to_domain(row)

    def list_locations(self) -> list[Location]:
        rows = self._session.scalars(select(LocationRow).order_by(LocationRow.location_id))
        return [mappers.location_to_domain(row) for row in rows]

    def get_subject(self, subject_id: int) -> Subject | None:
        row = self._session.get(SubjectRow, subject_id)
        return None if row is None else mappers.subject_to_domain(row)

    def list_subjects(self) -> list[Subject]:
        rows = self._session.scalars(select(SubjectRow).order_by(SubjectRow.subject_id))
        return [mappers.subject_to_domain(row) for row in rows]


class SqlAlchemyCameraRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, camera_id: int) -> Camera | None:
        row = self._session.get(CameraRow, camera_id)
        return None if row is None else mappers.camera_to_domain(row)

    def list_all(self) -> list[Camera]:
        rows = self._session.scalars(select(CameraRow).order_by(CameraRow.camera_id))
        return [mappers.camera_to_domain(row) for row in rows]

    def update(self, camera: Camera) -> None:
        row = None if camera.id is None else self._session.get(CameraRow, camera.id)
        if row is None:
            raise NotFoundError("Cámara", camera.id)
        mappers.apply_camera(camera, row)
        self._session.flush()

    def get_zone(self, zone_id: int) -> Zone | None:
        row = self._session.get(ZoneRow, zone_id)
        return None if row is None else mappers.zone_to_domain(row)

    def list_zones(self) -> list[Zone]:
        rows = self._session.scalars(select(ZoneRow).order_by(ZoneRow.zone_id))
        return [mappers.zone_to_domain(row) for row in rows]


class SqlAlchemyEventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_id: int) -> Event | None:
        row = self._session.get(EventRow, event_id)
        return None if row is None else mappers.event_to_domain(row)

    def add(self, event: Event) -> Event:
        row = mappers.event_to_row(event)
        self._session.add(row)
        self._session.flush()
        return mappers.event_to_domain(row)

    def update(self, event: Event) -> None:
        row = None if event.id is None else self._session.get(EventRow, event.id)
        if row is None:
            raise NotFoundError("Evento", event.id)
        mappers.apply_event(event, row)
        self._session.flush()

    def find(self, criteria: EventFilter, limit: int | None = None) -> list[Event]:
        statement = _filtered(select(EventRow), criteria).order_by(
            EventRow.occurred_at.desc(), EventRow.event_id.desc()
        )
        if limit is not None:
            statement = statement.limit(limit)
        return [mappers.event_to_domain(row) for row in self._session.scalars(statement)]

    def count(self, criteria: EventFilter) -> int:
        statement = _filtered(select(func.count(EventRow.event_id)), criteria)
        return self._session.scalar(statement) or 0


def _filtered[S: Select](statement: S, criteria: EventFilter) -> S:
    if criteria.statuses is not None:
        statement = statement.where(EventRow.status.in_([s.value for s in criteria.statuses]))
    if criteria.event_type_ids is not None:
        statement = statement.where(EventRow.event_type_id.in_(criteria.event_type_ids))
    if criteria.camera_ids is not None:
        statement = statement.where(EventRow.camera_id.in_(criteria.camera_ids))
    return statement


class SqlAlchemyAlertRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, alert_id: int) -> Alert | None:
        row = self._session.get(AlertRow, alert_id)
        return None if row is None else mappers.alert_to_domain(row)

    def add(self, alert: Alert) -> Alert:
        row = mappers.alert_to_row(alert)
        self._session.add(row)
        self._session.flush()
        return mappers.alert_to_domain(row)

    def update(self, alert: Alert) -> None:
        row = None if alert.id is None else self._session.get(AlertRow, alert.id)
        if row is None:
            raise NotFoundError("Alerta", alert.id)
        mappers.apply_alert(alert, row)
        self._session.flush()

    def find_by_event(self, event_id: int) -> list[Alert]:
        rows = self._session.scalars(
            select(AlertRow).where(AlertRow.event_id == event_id).order_by(AlertRow.alert_id)
        )
        return [mappers.alert_to_domain(row) for row in rows]
