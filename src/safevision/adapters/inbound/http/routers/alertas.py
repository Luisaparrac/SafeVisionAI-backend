"""Pending alerts, in the order kept by the priority queue, and panel metrics."""

from fastapi import APIRouter, Depends, Query

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container
from safevision.adapters.inbound.http.schemas import AlertOut, MetricsOut

router = APIRouter(prefix="/api", tags=["alertas"])


@router.get("/alertas/pendientes", response_model=list[AlertOut])
def pending_alerts(
    limit: int = Query(10, ge=1, le=100), container: Container = Depends(get_container)
) -> list[AlertOut]:
    """Most urgent first: highest severity, then oldest (max-heap)."""
    return [AlertOut.from_view(view) for view in container.get_pending_alerts.execute(limit)]


@router.patch(
    "/alertas/{alert_id}/vista",
    response_model=AlertOut,
    responses={409: {"description": "La alerta ya fue atendida o descartada"}},
)
def mark_alert_seen(alert_id: int, container: Container = Depends(get_container)) -> AlertOut:
    """Records that someone saw the alert; it stays pending until its event is closed."""
    return AlertOut.from_view(container.mark_alert_seen.execute(alert_id))


@router.get("/metricas", response_model=MetricsOut)
def metrics(container: Container = Depends(get_container)) -> MetricsOut:
    """Total events, pending alerts and high-priority events."""
    return MetricsOut.from_metrics(container.get_metrics.execute())
