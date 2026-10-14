import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.mark_false_alarm import MarkFalseAlarm
from safevision.domain.errors import InvalidTransitionError, NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import AlertStatus, EventStatus, Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


@pytest.fixture
def board() -> AlertBoard:
    return AlertBoard(history_capacity=10)


@pytest.fixture
def mark(uow, clock, board, presenter) -> MarkFalseAlarm:
    return MarkFalseAlarm(uow, clock, board, presenter)


def stored_event(uow, clock, board, presenter, status: str = "pending") -> Event:
    event = uow.events.add(
        Event(camera_id=1, event_type_id=2, occurred_at=clock.now(), status=status)
    )
    uow.alerts.add(Alert(event_id=event.id, level=2, created_at=event.occurred_at))
    uow.commit()
    board.add(AlertEntry(event.id, Severity(2), event.occurred_at), presenter.present(uow, event))
    return event


@pytest.mark.parametrize("status", ["pending", "in_review"])
def test_marks_false_alarm_and_dismisses_alerts(mark, uow, clock, board, presenter, status):
    event = stored_event(uow, clock, board, presenter, status)
    clock.advance(5)
    view = mark.execute(event.id)
    assert view.status == "Revisado"
    assert uow.events.get(event.id).status is EventStatus.FALSE_ALARM
    [alert] = uow.alerts.find_by_event(event.id)
    assert (alert.status, alert.attended_at) == (AlertStatus.DISMISSED, clock.now())
    assert board.pending_count() == 0


def test_repeating_is_a_no_op(mark, uow, clock, board, presenter):
    event = stored_event(uow, clock, board, presenter)
    mark.execute(event.id)
    commits = uow.commits
    assert mark.execute(event.id).status == "Revisado"
    assert uow.commits == commits


def test_resolved_event_cannot_become_false_alarm(mark, uow, clock, board, presenter):
    event = stored_event(uow, clock, board, presenter)
    resolved = uow.events.get(event.id)
    resolved.resolve()
    uow.events.update(resolved)
    uow.commit()
    with pytest.raises(InvalidTransitionError):
        mark.execute(event.id)
    assert uow.events.get(event.id).status is EventStatus.RESOLVED


def test_unknown_event(mark):
    with pytest.raises(NotFoundError):
        mark.execute(42)
