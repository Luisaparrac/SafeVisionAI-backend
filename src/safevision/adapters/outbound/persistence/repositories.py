"""SQLAlchemy implementations of the repository ports.

Each repository works on the session of the current unit of work: it flushes
its changes so ids and constraints are checked at once, but never commits.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence import mappers
from safevision.adapters.outbound.persistence.orm import EventTypeRow, LocationRow, SubjectRow
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject


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
