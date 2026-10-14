from datetime import timedelta

import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.rebuild_alert_board import RebuildAlertBoard
from safevision.domain.errors import NotFoundError
from safevision.domain.model.event import Event
from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


def add(uow, clock, minutes, event_type_id, status="pending"):
    occurred = clock.now() + timedelta(minutes=minutes)
    uow.events.add(
        Event(camera_id=1, event_type_id=event_type_id, occurred_at=occurred, status=status)
    )


def test_rebuilds_queue_and_history_from_the_database(uow, clock, presenter):
    # event types: 1 Caída (4), 2 Merodeo (2), 3 Ruido (1), 4 Humo (3)
    add(uow, clock, 0, 3)
    add(uow, clock, 1, 1, status="resolved")
    add(uow, clock, 2, 2, status="in_review")
    add(uow, clock, 3, 4)
    add(uow, clock, 4, 2, status="false_alarm")
    uow.commit()
    board = AlertBoard(history_capacity=3)
    board.add(AlertEntry(99, Severity(4), clock.now()), presenter.present(uow, uow.events.get(1)))

    assert RebuildAlertBoard(uow, board, presenter).execute() == 3
    assert [e.event_id for e in board.pending(10)] == [4, 3, 1]
    assert board.pending(1)[0].severity == Severity(3)
    assert [v.id for v in board.recent(10)] == [5, 4, 3]
    assert uow.commits == 1


def test_empty_database(uow, presenter):
    board = AlertBoard(history_capacity=5)
    assert RebuildAlertBoard(uow, board, presenter).execute() == 0
    assert board.recent(5) == []


def test_unknown_event_type_fails_without_touching_the_board(uow, clock, presenter):
    add(uow, clock, 0, 9)
    uow.commit()
    board = AlertBoard(history_capacity=5)
    with pytest.raises(NotFoundError):
        RebuildAlertBoard(uow, board, presenter).execute()
    assert board.pending_count() == 0
