"""Shared flow of the use cases that take an event out of the pending state."""

from datetime import datetime

from safevision.application.dto import EVENT_CLOSED, AlertNotification, EventView
from safevision.application.ports.clock import Clock
from safevision.application.ports.notifier import AlertNotifier
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event


class CloseEvent:
    """Closes an open event and its open alerts in one transaction.

    Subclasses decide how the event and its alerts are closed, and what to do
    when the event was already closed.
    """

    def __init__(
        self,
        uow: UnitOfWork,
        clock: Clock,
        board: AlertBoard,
        presenter: EventPresenter,
        notifier: AlertNotifier | None = None,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._board = board
        self._presenter = presenter
        self._notifier = notifier

    def execute(self, event_id: int) -> EventView:
        with self._uow as uow:
            event = uow.events.get(event_id)
            if event is None:
                raise NotFoundError("Evento", event_id)
            closed_now = event.is_open
            if closed_now:
                self._close_event(event)
                uow.events.update(event)
                now = self._clock.now()
                for alert in uow.alerts.find_by_event(event_id):
                    if alert.is_open:
                        # The database clock may run slightly behind the app clock.
                        self._close_alert(alert, max(now, alert.created_at))
                        uow.alerts.update(alert)
                uow.commit()
            else:
                self._when_already_closed(event)
            view = self._presenter.present(uow, event)
        self._board.close(view)
        if closed_now and self._notifier is not None:
            self._notifier.publish(AlertNotification(EVENT_CLOSED, view))
        return view

    def _close_event(self, event: Event) -> None:
        raise NotImplementedError

    def _close_alert(self, alert: Alert, at: datetime) -> None:
        raise NotImplementedError

    def _when_already_closed(self, event: Event) -> None:
        """Default: closing again is a no-op."""
