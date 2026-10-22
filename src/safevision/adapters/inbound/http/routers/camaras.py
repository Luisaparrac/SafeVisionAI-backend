"""Cameras: catalog for the panel and status reported by the IoT module."""

from fastapi import APIRouter, Depends

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import CameraOut, CameraStatusIn, CameraStatusOut
from safevision.adapters.inbound.http.security import (
    AUTH_RESPONSES,
    require_iot_key,
    require_panel_access,
)

router = APIRouter(prefix="/api/camaras", tags=["cámaras"], responses=AUTH_RESPONSES)


@router.get("", response_model=list[CameraOut], dependencies=[Depends(require_panel_access)])
def list_cameras(container: Container = Depends(get_container)) -> list[CameraOut]:
    return [CameraOut.from_entity(camera) for camera in container.list_cameras.execute()]


@router.patch(
    "/{camera_id}/estado",
    response_model=CameraStatusOut,
    dependencies=[Depends(require_iot_key)],
)
def update_camera_status(
    camera_id: int, data: CameraStatusIn, container: Container = Depends(get_container)
) -> CameraStatusOut:
    """Requires the X-API-Key header of the IoT module."""
    camera = container.update_camera_status.execute(camera_id, data.status)
    return CameraStatusOut.from_entity(camera)
