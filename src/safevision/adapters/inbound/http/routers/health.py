"""Service information and liveness probe used by the hosting platform."""

from fastapi import APIRouter

router = APIRouter(tags=["salud"])


@router.get("/")
def root() -> dict[str, str]:
    return {"servicio": "SafeVision AI backend", "docs": "/docs"}


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
