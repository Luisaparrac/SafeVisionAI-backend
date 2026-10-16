"""Use cases running on the real persistence adapters, as they will in production."""

from datetime import timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.orm import AlertRow, EventRow
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.application.services.event_deduplicator import EventDeduplicator
from safevision.application.use_cases.get_pending_alerts import GetPendingAlerts
from safevision.application.use_cases.mark_false_alarm import MarkFalseAlarm
from safevision.application.use_cases.rebuild_alert_board import RebuildAlertBoard
from safevision.application.use_cases.register_event import RegisterEvent, RegisterEventCommand
from safevision.application.use_cases.review_event import ReviewEvent

pytestmark = pytest.mark.integration


@pytest.fixture
def wiring(pg_seeded):
    clock = SystemClock()
    uow = SqlAlchemyUnitOfWork(make_session_factory(pg_seeded))
    board = AlertBoard(history_capacity=10)
    presenter = EventPresenter(ZoneInfo("America/Bogota"))
    deduplicator = EventDeduplicator(timedelta(seconds=10), clock.now)
    return {
        "register": RegisterEvent(uow, clock, board, deduplicator, presenter),
        "review": ReviewEvent(uow, clock, board, presenter),
        "false_alarm": MarkFalseAlarm(uow, clock, board, presenter),
        "pending": GetPendingAlerts(uow, board, presenter),
        "rebuild": RebuildAlertBoard(uow, AlertBoard(history_capacity=10), presenter),
        "engine": pg_seeded,
    }


def test_register_stores_event_and_alert(wiring):
    result = wiring["register"].execute(
        RegisterEventCommand(camera_id=1, event_type="caída", zone_id=1, confidence=0.9)
    )
    assert result.created
    assert result.view.location == "Casa · Escalera"
    with Session(wiring["engine"]) as session:
        event = session.get(EventRow, result.view.id)
        alert = session.scalars(select(AlertRow).where(AlertRow.event_id == event.event_id)).one()
    assert (event.status, event.zone_id) == ("pending", 1)
    assert (alert.level, alert.status, alert.created_at) == (4, "active", event.occurred_at)


def test_repeated_detection_reuses_the_stored_event(wiring):
    first = wiring["register"].execute(RegisterEventCommand(camera_id=1, event_type_id=2))
    again = wiring["register"].execute(RegisterEventCommand(camera_id=1, event_type_id=2))
    assert (again.created, again.view.id) == (False, first.view.id)
    with Session(wiring["engine"]) as session:
        assert session.scalar(select(EventRow.event_id).where(EventRow.event_id > 1)) is None


def test_review_closes_event_and_alert_satisfying_the_constraints(wiring):
    view = wiring["register"].execute(RegisterEventCommand(camera_id=2, event_type_id=4)).view
    reviewed = wiring["review"].execute(view.id)
    assert reviewed.status == "Revisado"
    assert wiring["pending"].execute(limit=10) == []
    with Session(wiring["engine"]) as session:
        alert = session.scalars(select(AlertRow)).one()
    assert alert.status == "resolved"
    assert alert.attended_at >= alert.created_at


def test_rebuild_reads_open_events_from_the_database(wiring):
    wiring["register"].execute(RegisterEventCommand(camera_id=1, event_type_id=3))
    wiring["register"].execute(RegisterEventCommand(camera_id=2, event_type_id=1, subject_id=1))
    assert wiring["rebuild"].execute() == 2


def test_false_alarm_dismisses_the_alert_satisfying_the_constraints(wiring):
    view = wiring["register"].execute(RegisterEventCommand(camera_id=1, event_type_id=1)).view
    wiring["false_alarm"].execute(view.id)
    with Session(wiring["engine"]) as session:
        event = session.get(EventRow, view.id)
        alert = session.scalars(select(AlertRow)).one()
    assert event.status == "false_alarm"
    assert alert.status == "dismissed"
    assert alert.attended_at >= alert.created_at
