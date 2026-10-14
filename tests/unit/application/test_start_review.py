import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.start_review import StartReview
from safevision.domain.errors import InvalidTransitionError, NotFoundError
from safevision.domain.model.event import Event
from safevision.domain.model.values import EventStatus, Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


@pytest.fixture
def board() -> AlertBoard:
    return AlertBoard(history_capacity=10)


@pytest.fixture
def start(uow, board, presenter) -> StartReview:
    return StartReview(uow, board, presenter)


def stored(uow, clock, status: str = "pending") -> Event:
    event = uow.events.add(
        Event(camera_id=1, event_type_id=1, occurred_at=clock.now(), status=status)
    )
    uow.commit()
    return event


def test_pending_event_goes_to_review_and_stays_pending(start, uow, clock, board, presenter):
    event = stored(uow, clock)
    board.add(AlertEntry(event.id, Severity(4), event.occurred_at), presenter.present(uow, event))
    view = start.execute(event.id)
    assert view.status == "Pendiente"
    assert uow.events.get(event.id).status is EventStatus.IN_REVIEW
    assert board.pending_count() == 1
    assert uow.commits == 2


def test_repeating_is_a_no_op(start, uow, clock):
    event = stored(uow, clock, status="in_review")
    start.execute(event.id)
    assert uow.commits == 1


@pytest.mark.parametrize("status", ["resolved", "false_alarm"])
def test_closed_event_cannot_be_reopened(start, uow, clock, status):
    event = stored(uow, clock, status=status)
    with pytest.raises(InvalidTransitionError):
        start.execute(event.id)
    assert uow.events.get(event.id).status is EventStatus(status)


def test_unknown_event(start):
    with pytest.raises(NotFoundError):
        start.execute(5)
