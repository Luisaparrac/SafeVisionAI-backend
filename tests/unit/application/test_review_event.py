from datetime import timedelta

import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.review_event import ReviewEvent
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import AlertStatus, EventStatus, Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


@pytest.fixture
def board() -> AlertBoard:
    return AlertBoard(history_capacity=10)


@pytest.fixture
def review(uow, clock, board, presenter) -> ReviewEvent:
    return ReviewEvent(uow, clock, board, presenter)


def pending_event(uow, clock, board, presenter, **overrides) -> Event:
    event = uow.events.add(
        Event(**({"camera_id": 1, "event_type_id": 1, "occurred_at": clock.now()} | overrides))
    )
    uow.alerts.add(Alert(event_id=event.id, level=4, created_at=event.occurred_at))
    uow.commit()
    board.add(AlertEntry(event.id, Severity(4), event.occurred_at), presenter.present(uow, event))
    return event


def test_resolves_event_and_closes_open_alerts(review, uow, clock, board, presenter):
    event = pending_event(uow, clock, board, presenter)
    uow.alerts.add(
        Alert(
            event_id=event.id,
            level=4,
            created_at=event.occurred_at,
            status="dismissed",
            attended_at=event.occurred_at,
        )
    )
    uow.commit()
    clock.advance(60)
    view = review.execute(event.id)
    assert view.status == "Revisado"
    assert uow.events.get(event.id).status is EventStatus.RESOLVED
    first, second = uow.alerts.find_by_event(event.id)
    assert (first.status, first.attended_at) == (AlertStatus.RESOLVED, clock.now())
    assert second.status is AlertStatus.DISMISSED  # already closed alerts are untouched
    assert board.pending_count() == 0
    assert board.recent(1)[0].status == "Revisado"


def test_in_review_event_can_be_resolved(review, uow, clock, board, presenter):
    event = pending_event(uow, clock, board, presenter, status="in_review")
    assert review.execute(event.id).status == "Revisado"


def test_reviewing_a_closed_event_is_idempotent(review, uow, clock, board, presenter):
    event = pending_event(uow, clock, board, presenter)
    review.execute(event.id)
    commits = uow.commits
    clock.advance(60)
    assert review.execute(event.id).status == "Revisado"
    assert uow.commits == commits
    assert uow.alerts.find_by_event(event.id)[0].attended_at == clock.now() - timedelta(seconds=60)


def test_false_alarm_stays_false_alarm(review, uow, clock, board, presenter):
    event = pending_event(uow, clock, board, presenter, status="false_alarm")
    review.execute(event.id)
    assert uow.events.get(event.id).status is EventStatus.FALSE_ALARM


def test_alert_created_after_app_clock_is_closed_at_its_creation_time(
    review, uow, clock, board, presenter
):
    event = pending_event(uow, clock, board, presenter)
    later = clock.now() + timedelta(seconds=2)
    uow.alerts.add(Alert(event_id=event.id, level=4, created_at=later))
    uow.commit()
    review.execute(event.id)
    assert uow.alerts.find_by_event(event.id)[1].attended_at == later


def test_unknown_event(review):
    with pytest.raises(NotFoundError, match="Evento 99"):
        review.execute(99)


def test_closing_is_published_once(uow, clock, board, presenter):
    from safevision.application.dto import EVENT_CLOSED
    from tests.fakes.notifier import RecordingNotifier

    notifier = RecordingNotifier()
    review = ReviewEvent(uow, clock, board, presenter, notifier)
    event = pending_event(uow, clock, board, presenter)
    view = review.execute(event.id)
    review.execute(event.id)  # already closed: nothing new to tell
    assert [(n.kind, n.event, n.alert) for n in notifier.published] == [(EVENT_CLOSED, view, None)]
