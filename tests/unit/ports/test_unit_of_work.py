from datetime import UTC, datetime

import pytest

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.event import Event
from tests.fakes.unit_of_work import FakeUnitOfWork

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def new_event() -> Event:
    return Event(camera_id=1, event_type_id=1, occurred_at=T0)


def test_fake_satisfies_the_port():
    assert isinstance(FakeUnitOfWork(), UnitOfWork)


def test_committed_changes_survive_the_block():
    uow = FakeUnitOfWork()
    with uow:
        uow.events.add(new_event())
        uow.commit()
    assert uow.events.get(1) is not None
    assert uow.commits == 1


def test_leaving_without_commit_discards_changes():
    uow = FakeUnitOfWork()
    with uow:
        uow.events.add(new_event())
    assert uow.events.get(1) is None
    assert uow.commits == 0


def test_exception_discards_uncommitted_changes_only():
    uow = FakeUnitOfWork()
    with uow:
        uow.events.add(new_event())
        uow.commit()
    with pytest.raises(RuntimeError), uow:
        uow.events.add(new_event())
        raise RuntimeError("boom")
    assert uow.events.get(1) is not None
    assert uow.events.get(2) is None


def test_explicit_rollback():
    uow = FakeUnitOfWork()
    with uow:
        uow.events.add(new_event())
        uow.rollback()
        assert uow.events.get(1) is None
