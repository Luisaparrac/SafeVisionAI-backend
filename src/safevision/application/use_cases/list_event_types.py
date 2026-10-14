"""Catalog of event types, most severe first."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.event_type import EventType


class ListEventTypes:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[EventType]:
        with self._uow as uow:
            return uow.event_types.list_all()
