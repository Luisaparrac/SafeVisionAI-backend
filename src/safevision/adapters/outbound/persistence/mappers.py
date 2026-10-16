"""Translation between ORM rows and domain entities.

Rows never leave the persistence adapter: repositories return entities built
here, so the domain rules are checked on every read as well.
"""

from safevision.adapters.outbound.persistence.orm import EventTypeRow, LocationRow, SubjectRow
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject


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
