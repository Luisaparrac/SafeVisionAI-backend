"""Marks a pending event as being reviewed; it stays open and its alert pending."""

from safevision.application.dto import EventView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.domain.errors import NotFoundError
from safevision.domain.model.values import EventStatus


class StartReview:
    def __init__(self, uow: UnitOfWork, board: AlertBoard, presenter: EventPresenter) -> None:
        self._uow = uow
        self._board = board
        self._presenter = presenter

    def execute(self, event_id: int) -> EventView:
        """Repeating it is a no-op; a closed event cannot be reopened."""
        with self._uow as uow:
            event = uow.events.get(event_id)
            if event is None:
                raise NotFoundError("Evento", event_id)
            if event.status is not EventStatus.IN_REVIEW:
                event.start_review()
                uow.events.update(event)
                uow.commit()
            view = self._presenter.present(uow, event)
        self._board.refresh(view)
        return view
