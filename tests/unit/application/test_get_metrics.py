from safevision.application.dto import Metrics
from safevision.application.services.alert_board import AlertBoard
from safevision.application.use_cases.get_metrics import GetMetrics
from safevision.domain.model.event import Event
from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry


def test_empty_system(uow):
    assert GetMetrics(uow, AlertBoard(10)).execute() == Metrics(total=0, pending=0, high=0)


def test_counts(uow, clock, presenter):
    board = AlertBoard(10)
    # event types: 1 Caída (4), 2 Merodeo (2), 3 Ruido (1), 4 Humo (3)
    for event_type_id, status in [(1, "pending"), (4, "resolved"), (2, "pending"), (3, "resolved")]:
        uow.events.add(
            Event(camera_id=1, event_type_id=event_type_id, occurred_at=clock.now(), status=status)
        )
    uow.commit()
    for event_id in (1, 3):
        event = uow.events.get(event_id)
        board.add(AlertEntry(event_id, Severity(2), clock.now()), presenter.present(uow, event))
    assert GetMetrics(uow, board).execute() == Metrics(total=4, pending=2, high=2)
