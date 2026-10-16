"""SQLAlchemy implementations of the repository ports.

Each repository works on the session of the current unit of work: it flushes
its changes so ids and constraints are checked at once, but never commits.
"""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence import mappers
from safevision.adapters.outbound.persistence.orm import EventTypeRow
from safevision.domain.model.event_type import EventType


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
