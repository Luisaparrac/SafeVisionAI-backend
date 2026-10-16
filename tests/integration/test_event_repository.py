from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from safevision.adapters.outbound.persistence.orm import EventRow
from safevision.adapters.outbound.persistence.repositories import SqlAlchemyEventRepository
from safevision.application.ports.repositories import EventFilter, EventRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event
from safevision.domain.model.values import Confidence, EventStatus

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
ALL = EventFilter()


def new_event(minutes: int = 0, **overrides) -> Event:
    data = {"camera_id": 1, "event_type_id": 1, "occurred_at": T0 + timedelta(minutes=minutes)}
    return Event(**(data | overrides))


@pytest.fixture
def repo(session):
    return SqlAlchemyEventRepository(session)


def test_satisfies_the_port(repo):
    assert isinstance(repo, EventRepository)


def test_add_assigns_ids_and_keeps_every_field(repo):
    first = repo.add(new_event())
    second = repo.add(
        new_event(
            zone_id=1,
            subject_id=1,
            detected_class="cat",
            confidence=0.87,
            evidence_url="https://example.com/e.jpg",
            description="Algo pasó",
        )
    )
    assert (first.id, second.id) == (1, 2)
    loaded = repo.get(2)
    assert loaded == second
    assert loaded.confidence == Confidence(0.87)
    assert loaded.occurred_at == T0
    assert repo.get(99) is None


def test_update_persists_changes(repo, session):
    event = repo.add(new_event())
    event.start_review()
    repo.update(event)
    stored = session.scalar(select(EventRow.status).where(EventRow.event_id == event.id))
    assert stored == "in_review"


def test_update_of_missing_event_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(new_event(id=5))


def test_find_newest_first_with_id_as_tie_breaker(repo):
    repo.add(new_event(minutes=0))
    repo.add(new_event(minutes=5))
    repo.add(new_event(minutes=5))
    assert [e.id for e in repo.find(ALL)] == [3, 2, 1]
    assert [e.id for e in repo.find(ALL, limit=2)] == [3, 2]


def test_find_and_count_by_status_and_type(repo):
    repo.add(new_event(event_type_id=1))
    repo.add(new_event(event_type_id=2, status="resolved"))
    repo.add(new_event(event_type_id=3, status="in_review"))
    open_events = EventFilter(statuses=(EventStatus.PENDING, EventStatus.IN_REVIEW))
    assert [e.id for e in repo.find(open_events)] == [3, 1]
    assert repo.count(open_events) == 2
    by_type = EventFilter(event_type_ids=(2, 3))
    assert {e.id for e in repo.find(by_type)} == {2, 3}
    assert repo.count(EventFilter(statuses=open_events.statuses, event_type_ids=(2,))) == 0
    assert repo.count(ALL) == 3


def test_empty_type_list_matches_nothing(repo):
    repo.add(new_event())
    assert repo.find(EventFilter(event_type_ids=())) == []
    assert repo.count(EventFilter(event_type_ids=())) == 0


def test_find_and_count_by_camera(repo):
    repo.add(new_event(camera_id=1))
    repo.add(new_event(camera_id=2, minutes=1))
    repo.add(new_event(camera_id=1, minutes=2))
    assert [e.id for e in repo.find(EventFilter(camera_ids=(1,)))] == [3, 1]
    assert repo.count(EventFilter(camera_ids=(2,))) == 1
    assert repo.find(EventFilter(camera_ids=())) == []


def test_find_by_time_range(repo):
    repo.add(new_event(minutes=0))
    repo.add(new_event(minutes=10))
    repo.add(new_event(minutes=20))
    window = EventFilter(
        occurred_from=T0 + timedelta(minutes=10), occurred_before=T0 + timedelta(minutes=20)
    )
    assert [e.id for e in repo.find(window)] == [2]
    assert repo.count(EventFilter(occurred_from=T0 + timedelta(minutes=10))) == 2
