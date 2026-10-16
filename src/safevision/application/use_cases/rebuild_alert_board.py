"""Reloads the in-memory board from the database, the source of truth, on startup."""

from safevision.application.ports.repositories import EventFilter
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.errors import NotFoundError
from safevision.domain.model.identity import require_id
from safevision.domain.model.values import ReviewLabel
from safevision.domain.structures.alert_priority_queue import AlertEntry


class RebuildAlertBoard:
    def __init__(self, uow: UnitOfWork, board: AlertBoard, presenter: EventPresenter) -> None:
        self._uow = uow
        self._board = board
        self._presenter = presenter

    def execute(self) -> int:
        """Queues every open event and loads the latest ones; returns the pending count."""
        with self._uow as uow:
            severities = {t.id: t.severity for t in uow.event_types.list_all()}
            entries: list[AlertEntry] = []
            for event in uow.events.find(EventFilter(statuses=ReviewLabel.PENDING.statuses)):
                if event.event_type_id not in severities:
                    raise NotFoundError("Tipo de evento", event.event_type_id)
                entries.append(
                    AlertEntry(
                        require_id(event.id), severities[event.event_type_id], event.occurred_at
                    )
                )
            recent = uow.events.find(EventFilter(), limit=self._board.history_capacity)
            views = self._presenter.present_many(uow, recent)
        self._board.replace(entries, views)
        return len(entries)
