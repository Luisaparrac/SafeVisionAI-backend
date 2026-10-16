"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.errors import install_error_handlers
from safevision.adapters.inbound.http.routers import catalogos, health

DESCRIPTION = (
    "API de SafeVision AI: recibe las detecciones del módulo IoT y sirve al panel "
    "los eventos, las alertas pendientes (cola de prioridad) y los catálogos."
)

TAGS = [
    {"name": "salud", "description": "Información del servicio y estado."},
    {"name": "catálogos", "description": "Tipos de evento, ubicaciones, zonas y sujetos."},
]


def create_app(container: Container) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        # The database is the source of truth: reload the in-memory structures on startup.
        container.rebuild_alert_board.execute()
        yield

    app = FastAPI(
        title="SafeVision AI - Backend",
        version="2.0.0",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
    )
    app.state.container = container
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(container.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(catalogos.router)
    return app
