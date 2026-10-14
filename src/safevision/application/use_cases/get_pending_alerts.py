"""Pending alerts in attention order, as kept by the priority queue."""

from safevision.application.dto import AlertView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.model.values import AlertStatus


class GetPendingAlerts:
    def __init__(self, uow: UnitOfWork, board: AlertBoard, presenter: EventPresenter) -> None:
        self._uow = uow
        self._board = board
        self._presenter = presenter

    def execute(self, limit: int) -> list[AlertView]:
        """Most urgent first: highest severity, then oldest.

        Events deleted from the database behind the application's back are skipped.
        """
        views: list[AlertView] = []
        with self._uow as uow:
            for entry in self._board.pending(limit):
                event = uow.events.get(entry.event_id)
                if event is None:
                    continue
                alerts = uow.alerts.find_by_event(entry.event_id)
                if alerts:
                    views.append(self._presenter.present_alert(uow, alerts[-1]))
                else:
                    views.append(
                        AlertView(
                            alert_id=0,
                            level=entry.severity.priority.value,
                            status=AlertStatus.ACTIVE.label,
                            event=self._presenter.present(uow, event),
                        )
                    )
        return views
