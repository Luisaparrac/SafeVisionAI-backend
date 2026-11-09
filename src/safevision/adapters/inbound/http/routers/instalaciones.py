"""Locations, cameras and zones with the pending events of each one."""

from fastapi import APIRouter, Depends

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import InstallationsOut
from safevision.adapters.inbound.http.security import AUTH_RESPONSES, require_panel_access

router = APIRouter(
    prefix="/api/instalaciones",
    tags=["instalaciones"],
    dependencies=[Depends(require_panel_access)],
    responses=AUTH_RESPONSES,
)


@router.get("", response_model=InstallationsOut)
def get_installations(container: Container = Depends(get_container)) -> InstallationsOut:
    """Each level adds up the pending events below it and keeps the highest severity."""
    return InstallationsOut.from_view(container.get_installations.execute())
