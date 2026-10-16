"""Read-only catalogs used by the panel to fill its filters and forms."""

from fastapi import APIRouter, Depends

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import (
    EventTypeOut,
    LocationOut,
    SubjectOut,
    ZoneOut,
)

router = APIRouter(prefix="/api", tags=["catálogos"])


@router.get("/tipos-evento", response_model=list[EventTypeOut])
def list_event_types(container: Container = Depends(get_container)) -> list[EventTypeOut]:
    """Most severe first, then by name."""
    return [EventTypeOut.from_entity(t) for t in container.list_event_types.execute()]


@router.get("/ubicaciones", response_model=list[LocationOut])
def list_locations(container: Container = Depends(get_container)) -> list[LocationOut]:
    return [LocationOut.from_entity(loc) for loc in container.list_locations.execute()]


@router.get("/zonas", response_model=list[ZoneOut])
def list_zones(container: Container = Depends(get_container)) -> list[ZoneOut]:
    return [ZoneOut.from_entity(zone) for zone in container.list_zones.execute()]


@router.get("/sujetos", response_model=list[SubjectOut])
def list_subjects(container: Container = Depends(get_container)) -> list[SubjectOut]:
    return [SubjectOut.from_entity(s) for s in container.list_subjects.execute()]
