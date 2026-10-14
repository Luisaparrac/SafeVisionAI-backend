"""Status reported by the IoT module for one of its cameras."""

from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera


class UpdateCameraStatus:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, camera_id: int, status: str) -> Camera:
        with self._uow as uow:
            camera = uow.cameras.get(camera_id)
            if camera is None:
                raise NotFoundError("Cámara", camera_id)
            camera.change_status(status)
            uow.cameras.update(camera)
            uow.commit()
            return camera
