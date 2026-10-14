"""Marks an event as reviewed (resolved) and closes its open alerts."""

from safevision.application.dto import EventView
from safevision.application.ports.clock import Clock
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.errors import NotFoundError


class ReviewEvent:
    def __init__(
        self, uow: UnitOfWork, clock: Clock, board: AlertBoard, presenter: EventPresenter
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._board = board
        self._presenter = presenter

    def execute(self, event_id: int) -> EventView:
        """Idempotent: reviewing an already closed event returns it unchanged."""
        with self._uow as uow:
            event = uow.events.get(event_id)
            if event is None:
                raise NotFoundError("Evento", event_id)
            if event.is_open:
                event.resolve()
                uow.events.update(event)
                now = self._clock.now()
                for alert in uow.alerts.find_by_event(event_id):
                    if alert.is_open:
                        # The database clock may run slightly behind the app clock.
                        alert.close(max(now, alert.created_at))
                        uow.alerts.update(alert)
                uow.commit()
            view = self._presenter.present(uow, event)
        self._board.close(view)
        return view
