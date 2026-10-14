from datetime import timedelta

import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.get_pending_alerts import GetPendingAlerts
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


@pytest.fixture
def board() -> AlertBoard:
    return AlertBoard(history_capacity=10)


def add_pending(uow, board, presenter, clock, event_type_id, severity, minutes, alert=True):
    occurred = clock.now() + timedelta(minutes=minutes)
    event = uow.events.add(Event(camera_id=1, event_type_id=event_type_id, occurred_at=occurred))
    if alert:
        uow.alerts.add(Alert(event_id=event.id, level=severity, created_at=occurred))
    uow.commit()
    board.add(AlertEntry(event.id, Severity(severity), occurred), presenter.present(uow, event))
    return event


def test_order_follows_the_heap(uow, board, presenter, clock):
    add_pending(uow, board, presenter, clock, 3, 1, minutes=0)
    add_pending(uow, board, presenter, clock, 1, 4, minutes=5)
    add_pending(uow, board, presenter, clock, 4, 3, minutes=1)
    add_pending(uow, board, presenter, clock, 1, 4, minutes=2)
    views = GetPendingAlerts(uow, board, presenter).execute(limit=10)
    assert [v.event.id for v in views] == [4, 2, 3, 1]
    assert [v.level for v in views] == ["Alto", "Alto", "Alto", "Bajo"]
    assert views[0].alert_id == 4
    assert views[0].status == "Activa"


def test_limit(uow, board, presenter, clock):
    for minutes in range(5):
        add_pending(uow, board, presenter, clock, 2, 2, minutes)
    assert len(GetPendingAlerts(uow, board, presenter).execute(limit=3)) == 3


def test_latest_alert_of_the_event_is_shown(uow, board, presenter, clock):
    event = add_pending(uow, board, presenter, clock, 2, 2, minutes=0)
    seen = uow.alerts.add(
        Alert(event_id=event.id, level=2, created_at=event.occurred_at, status="seen")
    )
    uow.commit()
    [view] = GetPendingAlerts(uow, board, presenter).execute(limit=5)
    assert (view.alert_id, view.status) == (seen.id, "Vista")


def test_event_without_alert_uses_defaults(uow, board, presenter, clock):
    add_pending(uow, board, presenter, clock, 2, 2, minutes=0, alert=False)
    [view] = GetPendingAlerts(uow, board, presenter).execute(limit=5)
    assert (view.alert_id, view.level, view.status) == (0, "Medio", "Activa")


def test_events_missing_in_the_database_are_skipped(uow, board, presenter, clock):
    add_pending(uow, board, presenter, clock, 1, 4, minutes=0)
    board.add(AlertEntry(99, Severity(4), clock.now()), presenter.present(uow, uow.events.get(1)))
    views = GetPendingAlerts(uow, board, presenter).execute(limit=5)
    assert [v.event.id for v in views] == [1]


def test_empty_board(uow, board, presenter):
    assert GetPendingAlerts(uow, board, presenter).execute(limit=5) == []
