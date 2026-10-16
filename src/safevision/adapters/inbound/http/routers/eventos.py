"""Events: detections registered by the IoT module and reviewed from the panel."""

from fastapi import APIRouter, Depends, Query

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import EventIn, EventOut
from safevision.adapters.inbound.http.security import require_iot_key

router = APIRouter(prefix="/api/eventos", tags=["eventos"])


@router.get("", response_model=list[EventOut])
def list_events(
    q: str | None = None,
    prioridad: str | None = Query(None, description="Alto, Medio o Bajo"),
    estado: str | None = Query(None, description="Pendiente o Revisado"),
    container: Container = Depends(get_container),
) -> list[EventOut]:
    """Newest first. ``q`` searches the id, type, subject and location."""
    views = container.list_events.execute(q=q, priority=prioridad, status=estado)
    return [EventOut.from_view(view) for view in views]


# Declared before /{event_id} so "recientes" is not read as an id.
@router.get("/recientes", response_model=list[EventOut])
def recent_events(
    limit: int = Query(20, ge=1, le=100), container: Container = Depends(get_container)
) -> list[EventOut]:
    """Recent history kept in memory (doubly linked list), newest first."""
    return [EventOut.from_view(view) for view in container.get_recent_events.execute(limit)]


@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, container: Container = Depends(get_container)) -> EventOut:
    return EventOut.from_view(container.get_event.execute(event_id))


@router.post(
    "",
    response_model=EventOut,
    status_code=201,
    dependencies=[Depends(require_iot_key)],
)
def register_event(data: EventIn, container: Container = Depends(get_container)) -> EventOut:
    """Registers a detection of the IoT module (requires X-API-Key) and raises its alert."""
    result = container.register_event.execute(data.to_command())
    return EventOut.from_view(result.view)


@router.patch("/{event_id}/revisar", response_model=EventOut)
def review_event(event_id: int, container: Container = Depends(get_container)) -> EventOut:
    """Marks the event as reviewed and closes its alerts; repeating it changes nothing."""
    return EventOut.from_view(container.review_event.execute(event_id))
