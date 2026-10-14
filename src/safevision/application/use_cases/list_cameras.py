"""Catalog of cameras, by id."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.camera import Camera


class ListCameras:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self) -> list[Camera]:
        with self._uow as uow:
            return uow.cameras.list_all()
