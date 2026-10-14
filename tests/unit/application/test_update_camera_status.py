import pytest

from safevision.application.use_cases.update_camera_status import UpdateCameraStatus
from safevision.domain.errors import NotFoundError, ValidationError
from safevision.domain.model.values import CameraStatus


def test_updates_and_returns_the_camera(uow):
    camera = UpdateCameraStatus(uow).execute(2, "disconnected")
    assert (camera.id, camera.status) == (2, CameraStatus.DISCONNECTED)
    assert uow.cameras.get(2).status is CameraStatus.DISCONNECTED
    assert uow.commits == 1


def test_invalid_status_changes_nothing(uow):
    with pytest.raises(ValidationError):
        UpdateCameraStatus(uow).execute(2, "off")
    assert uow.cameras.get(2).status is CameraStatus.ACTIVE


def test_unknown_camera(uow):
    with pytest.raises(NotFoundError, match="Cámara 9"):
        UpdateCameraStatus(uow).execute(9, "active")
