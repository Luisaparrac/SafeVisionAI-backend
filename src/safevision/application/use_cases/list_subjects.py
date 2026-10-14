"""Catalog of monitored subjects, by id."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.subject import Subject


class ListSubjects:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Subject]:
        with self._uow as uow:
            return uow.catalog.list_subjects()
