"""Composition root: the only place that connects ports with their adapters."""

from datetime import timedelta

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.outbound.persistence.database import make_engine, make_session_factory
from safevision.adapters.outbound.persistence.readiness import DatabaseReadinessProbe
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.application.ports.clock import Clock
from safevision.application.ports.readiness import ReadinessProbe
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.application.services.alert_board import AlertBoard
from safevision.application.services.event_deduplicator import EventDeduplicator
from safevision.application.use_cases.get_event import GetEvent
from safevision.application.use_cases.get_metrics import GetMetrics
from safevision.application.use_cases.get_pending_alerts import GetPendingAlerts
from safevision.application.use_cases.get_recent_events import GetRecentEvents
from safevision.application.use_cases.list_cameras import ListCameras
from safevision.application.use_cases.list_event_types import ListEventTypes
from safevision.application.use_cases.list_events import ListEvents
from safevision.application.use_cases.list_locations import ListLocations
from safevision.application.use_cases.list_subjects import ListSubjects
from safevision.application.use_cases.list_zones import ListZones
from safevision.application.use_cases.mark_alert_seen import MarkAlertSeen
from safevision.application.use_cases.mark_false_alarm import MarkFalseAlarm
from safevision.application.use_cases.rebuild_alert_board import RebuildAlertBoard
from safevision.application.use_cases.register_event import RegisterEvent
from safevision.application.use_cases.review_event import ReviewEvent
from safevision.application.use_cases.update_camera_status import UpdateCameraStatus
from safevision.config.settings import Settings


class AlwaysReady:
    """Readiness of adapters that need no external service (in-memory)."""

    def is_ready(self) -> bool:
        return True


def build_container(
    settings: Settings,
    uow: UnitOfWork,
    clock: Clock,
    readiness: ReadinessProbe | None = None,
) -> Container:
    """Wires the use cases around one unit of work, one clock and one in-memory board."""
    presenter = EventPresenter(settings.tzinfo)
    board = AlertBoard(settings.history_capacity)
    deduplicator = EventDeduplicator(timedelta(seconds=settings.dedup_window_seconds), clock.now)
    return Container(
        iot_api_key=settings.iot_api_key,
        cors_origins=settings.frontend_origins,
        readiness=readiness or AlwaysReady(),
        rebuild_alert_board=RebuildAlertBoard(uow, board, presenter),
        register_event=RegisterEvent(uow, clock, board, deduplicator, presenter),
        review_event=ReviewEvent(uow, clock, board, presenter),
        mark_false_alarm=MarkFalseAlarm(uow, clock, board, presenter),
        get_event=GetEvent(uow, presenter),
        list_events=ListEvents(uow, presenter),
        get_recent_events=GetRecentEvents(board),
        get_pending_alerts=GetPendingAlerts(uow, board, presenter),
        mark_alert_seen=MarkAlertSeen(uow, presenter),
        get_metrics=GetMetrics(uow, board),
        list_event_types=ListEventTypes(uow),
        list_locations=ListLocations(uow),
        list_cameras=ListCameras(uow),
        update_camera_status=UpdateCameraStatus(uow),
        list_zones=ListZones(uow),
        list_subjects=ListSubjects(uow),
    )


def build_production_container(settings: Settings) -> Container:
    """PostgreSQL and the system clock. No connection is opened until the first query."""
    engine = make_engine(settings.database_url)
    uow = SqlAlchemyUnitOfWork(make_session_factory(engine))
    return build_container(settings, uow, SystemClock(), DatabaseReadinessProbe(engine))
