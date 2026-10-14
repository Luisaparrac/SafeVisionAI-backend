from datetime import timedelta

from safevision.application.services.alert_board import AlertBoard
from safevision.application.services.event_deduplicator import EventDeduplicator
from safevision.application.use_cases.get_recent_events import GetRecentEvents
from safevision.application.use_cases.register_event import RegisterEvent, RegisterEventCommand
from safevision.application.use_cases.review_event import ReviewEvent


def test_reflects_registered_and_reviewed_events(uow, clock, presenter):
    board = AlertBoard(history_capacity=2)
    register = RegisterEvent(
        uow, clock, board, EventDeduplicator(timedelta(0), clock.now), presenter
    )
    for event_type_id in (1, 2, 3):
        register.execute(RegisterEventCommand(camera_id=1, event_type_id=event_type_id))
        clock.advance(1)
    ReviewEvent(uow, clock, board, presenter).execute(3)
    recent = GetRecentEvents(board).execute(limit=10)
    assert [(v.id, v.status) for v in recent] == [(3, "Revisado"), (2, "Pendiente")]
    assert len(GetRecentEvents(board).execute(limit=1)) == 1
