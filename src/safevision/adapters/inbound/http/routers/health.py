"""Service information and liveness probe used by the hosting platform."""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.dependencies import get_container

router = APIRouter(tags=["salud"])


@router.get("/")
def root() -> dict[str, str]:
    return {"servicio": "SafeVision AI backend", "docs": "/docs"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", responses={503: {"description": "La base de datos no responde"}})
def ready(container: Container = Depends(get_container)) -> JSONResponse:
    """Readiness: also checks the database. /health stays a pure liveness probe."""
    if container.readiness.is_ready():
        return JSONResponse({"status": "ok", "database": "ok"})
    return JSONResponse({"status": "unavailable", "database": "error"}, status_code=503)
