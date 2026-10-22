"""Event statistics for the panel charts."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import CameraCountOut, EventTypeCountOut
from safevision.adapters.inbound.http.security import AUTH_RESPONSES, require_panel_access

router = APIRouter(
    prefix="/api/estadisticas",
    tags=["estadísticas"],
    dependencies=[Depends(require_panel_access)],
    responses=AUTH_RESPONSES,
)

DESDE = Query(None, description="Fecha local inicial (AAAA-MM-DD), inclusive")
HASTA = Query(None, description="Fecha local final (AAAA-MM-DD), inclusive")


@router.get("/tipos", response_model=list[EventTypeCountOut])
def by_event_type(
    desde: date | None = DESDE,
    hasta: date | None = HASTA,
    container: Container = Depends(get_container),
) -> list[EventTypeCountOut]:
    """Events per type, including types without events; most frequent first."""
    rows = container.event_type_statistics.execute(date_from=desde, date_to=hasta)
    return [EventTypeCountOut.model_validate(row) for row in rows]


@router.get("/camaras", response_model=list[CameraCountOut])
def by_camera(
    desde: date | None = DESDE,
    hasta: date | None = HASTA,
    container: Container = Depends(get_container),
) -> list[CameraCountOut]:
    """Events per camera, including cameras without events; most frequent first."""
    rows = container.camera_statistics.execute(date_from=desde, date_to=hasta)
    return [CameraCountOut.model_validate(row) for row in rows]
