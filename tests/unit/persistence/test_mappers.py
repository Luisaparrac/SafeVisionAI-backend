"""ORM rows <-> domain entities, using transient rows (no database)."""

import pytest

from safevision.adapters.outbound.persistence import mappers
from safevision.adapters.outbound.persistence.orm import EventTypeRow, LocationRow, SubjectRow
from safevision.domain.errors import ValidationError
from safevision.domain.model.values import Priority, Severity, SubjectType


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
