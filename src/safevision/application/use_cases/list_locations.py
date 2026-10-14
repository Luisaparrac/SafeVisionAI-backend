"""Catalog of monitored locations, by id."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.location import Location


class ListLocations:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Location]:
        with self._uow as uow:
            return uow.catalog.list_locations()
