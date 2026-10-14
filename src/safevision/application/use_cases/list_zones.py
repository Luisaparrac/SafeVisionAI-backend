"""Catalog of monitored zones, by id."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.zone import Zone


class ListZones:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Zone]:
        with self._uow as uow:
            return uow.cameras.list_zones()
