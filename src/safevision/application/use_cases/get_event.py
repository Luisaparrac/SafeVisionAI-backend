"""Detail of one event."""

from safevision.application.dto import EventView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.domain.errors import NotFoundError


class GetEvent:
    def __init__(self, uow: UnitOfWork, presenter: EventPresenter) -> None:
        self._uow = uow
        self._presenter = presenter

    def execute(self, event_id: int) -> EventView:
        with self._uow as uow:
            event = uow.events.get(event_id)
            if event is None:
                raise NotFoundError("Evento", event_id)
            return self._presenter.present(uow, event)
