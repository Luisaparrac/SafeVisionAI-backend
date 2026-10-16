"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.inbound.http.errors import install_error_handlers
from safevision.adapters.inbound.http.logging_setup import AccessLogMiddleware, configure_logging
from safevision.adapters.inbound.http.request_id import REQUEST_ID_HEADER, RequestIdMiddleware
from safevision.adapters.inbound.http.routers import (
    alertas,
    camaras,
    catalogos,
    estadisticas,
    eventos,
    health,
)
from safevision.adapters.inbound.http.routers.eventos import DUPLICATE_HEADER
from safevision.adapters.inbound.http.websocket import router as websocket_router

DESCRIPTION = (
    "API de SafeVision AI: recibe las detecciones del módulo IoT y sirve al panel "
    "los eventos, las alertas pendientes (cola de prioridad) y los catálogos."
)

TAGS = [
    {"name": "salud", "description": "Información del servicio y estado."},
    {"name": "eventos", "description": "Detecciones del módulo IoT y su revisión."},
    {"name": "alertas", "description": "Alertas pendientes por prioridad y métricas del panel."},
    {"name": "estadísticas", "description": "Conteos de eventos por tipo y por cámara."},
    {"name": "catálogos", "description": "Tipos de evento, ubicaciones, zonas y sujetos."},
    {"name": "cámaras", "description": "Cámaras y estado reportado por el módulo IoT."},
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
    app.add_middleware(AccessLogMiddleware)  # inside RequestIdMiddleware: sees the id
    app.add_middleware(RequestIdMiddleware)
    # Added last, so it is the outermost middleware and also answers preflight requests.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(container.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[DUPLICATE_HEADER, REQUEST_ID_HEADER],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(eventos.router)
    app.include_router(alertas.router)
    app.include_router(estadisticas.router)
    app.include_router(catalogos.router)
    app.include_router(camaras.router)
    app.include_router(websocket_router)
    return app


def create_app_from_env() -> FastAPI:
    """Production entry point: settings from the environment (and from .env when present).

    Only DATABASE_URL and IOT_API_KEY are required; if either is missing the
    process stops here instead of answering requests.
    """
    from dotenv import load_dotenv

    from safevision.bootstrap import build_production_container
    from safevision.config.settings import Settings

    load_dotenv()  # local runs; on the hosting platform the variables come from its dashboard
    settings = Settings.from_env()
    configure_logging(settings.log_level)
    return create_app(build_production_container(settings))


def __getattr__(name: str) -> FastAPI:
    # "uvicorn safevision.adapters.inbound.http.app:app" builds the application on
    # first access, so importing create_app (tests, tools) never reads the environment.
    if name != "app":
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    app = create_app_from_env()
    globals()["app"] = app
    return app
