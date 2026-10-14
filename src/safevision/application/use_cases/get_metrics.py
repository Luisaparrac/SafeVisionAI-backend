"""Numbers of the panel cards."""

from safevision.application.dto import Metrics
from safevision.application.ports.repositories import EventFilter
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.model.values import Priority


class GetMetrics:
    def __init__(self, uow: UnitOfWork, board: AlertBoard) -> None:
        self._uow = uow
        self._board = board

    def execute(self) -> Metrics:
        """Total events, pending alerts (size of the queue) and high-priority events."""
        with self._uow as uow:
            high_levels = Priority.HIGH.severity_levels
            high_types = tuple(
                t.id for t in uow.event_types.list_all() if t.severity.level in high_levels
            )
            total = uow.events.count(EventFilter())
            high = uow.events.count(EventFilter(event_type_ids=high_types))
        return Metrics(total=total, pending=self._board.pending_count(), high=high)
