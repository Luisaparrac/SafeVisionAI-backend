from datetime import UTC, datetime

import pytest

from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.domain.model.event import Event

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def uow(pg_seeded):
    return SqlAlchemyUnitOfWork(make_session_factory(pg_seeded))


def add_event(uow) -> int:
    return uow.events.add(Event(camera_id=1, event_type_id=1, occurred_at=T0)).id


def test_committed_changes_are_visible_in_the_next_block(uow):
    with uow:
        event_id = add_event(uow)
        uow.commit()
    with uow:
        assert uow.events.get(event_id) is not None


def test_changes_without_commit_are_discarded(uow):
    with uow:
        event_id = add_event(uow)
    with uow:
        assert uow.events.get(event_id) is None


def test_explicit_rollback(uow):
    with uow:
        event_id = add_event(uow)
        uow.rollback()
        assert uow.events.get(event_id) is None


def test_catalogs_are_reachable(uow):
    with uow:
        assert uow.event_types.find_by_name("Caída").id == 1
        assert uow.cameras.get(1).name == "Sala"
        assert uow.catalog.get_subject(1).name == "Rosa"
