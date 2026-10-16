"""Behavior expected from any EventRepository, checked on the in-memory fake."""

from datetime import UTC, datetime, timedelta

import pytest

from safevision.application.ports.repositories import EventFilter, EventRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event
from safevision.domain.model.values import EventStatus
from tests.fakes.repositories import InMemoryEventRepository

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
ALL = EventFilter()


def new_event(minutes: int = 0, **overrides) -> Event:
    data = {"camera_id": 1, "event_type_id": 1, "occurred_at": T0 + timedelta(minutes=minutes)}
    return Event(**(data | overrides))


@pytest.fixture
def repo() -> InMemoryEventRepository:
    return InMemoryEventRepository()


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, EventRepository)


def test_add_assigns_ids_and_get_returns_a_copy(repo):
    first, second = repo.add(new_event()), repo.add(new_event())
    assert (first.id, second.id) == (1, 2)
    loaded = repo.get(1)
    loaded.resolve()
    assert repo.get(1).status is EventStatus.PENDING
    assert repo.get(99) is None


def test_update_persists_changes(repo):
    event = repo.add(new_event())
    event.resolve()
    repo.update(event)
    assert repo.get(event.id).status is EventStatus.RESOLVED


def test_update_of_missing_event_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(new_event(id=5))


def test_find_orders_newest_first_with_id_as_tie_breaker(repo):
    repo.add(new_event(minutes=1))
    repo.add(new_event(minutes=5))
    repo.add(new_event(minutes=5))
    assert [e.id for e in repo.find(ALL)] == [3, 2, 1]
    assert [e.id for e in repo.find(ALL, limit=2)] == [3, 2]


def test_find_and_count_by_status_and_type(repo):
    repo.add(new_event(event_type_id=1))
    repo.add(new_event(event_type_id=2, status="resolved"))
    repo.add(new_event(event_type_id=3, status="in_review"))
    open_events = EventFilter(statuses=(EventStatus.PENDING, EventStatus.IN_REVIEW))
    assert {e.id for e in repo.find(open_events)} == {1, 3}
    assert repo.count(EventFilter(event_type_ids=(2, 3))) == 2
    assert repo.count(EventFilter(statuses=(EventStatus.RESOLVED,), event_type_ids=(1,))) == 0
    assert repo.count(EventFilter(event_type_ids=())) == 0
    assert repo.count(ALL) == 3


def test_find_and_count_by_camera(repo):
    repo.add(new_event(camera_id=1))
    repo.add(new_event(camera_id=2))
    repo.add(new_event(camera_id=3))
    assert [e.id for e in repo.find(EventFilter(camera_ids=(1, 3)))] == [3, 1]
    assert repo.count(EventFilter(camera_ids=(2,))) == 1


def test_find_pages_with_offset_and_limit(repo):
    for minutes in range(5):
        repo.add(new_event(minutes=minutes))
    assert [e.id for e in repo.find(ALL, limit=2, offset=1)] == [4, 3]
    assert [e.id for e in repo.find(ALL, offset=3)] == [2, 1]
    assert repo.find(ALL, limit=2, offset=10) == []
