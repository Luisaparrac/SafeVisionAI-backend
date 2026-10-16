"""What the HTTP adapter needs to work: the use cases and its own settings.

The composition root (``safevision.bootstrap``) builds it; the routers only
read it from the application state, so they never create infrastructure.
"""

from dataclasses import dataclass, field

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
from safevision.application.use_cases.rebuild_alert_board import RebuildAlertBoard
from safevision.application.use_cases.register_event import RegisterEvent
from safevision.application.use_cases.review_event import ReviewEvent
from safevision.application.use_cases.update_camera_status import UpdateCameraStatus


@dataclass(frozen=True, kw_only=True)
class Container:
    iot_api_key: str = field(repr=False)
    cors_origins: tuple[str, ...]

    rebuild_alert_board: RebuildAlertBoard
    register_event: RegisterEvent
    review_event: ReviewEvent
    get_event: GetEvent
    list_events: ListEvents
    get_recent_events: GetRecentEvents
    get_pending_alerts: GetPendingAlerts
    get_metrics: GetMetrics
    list_event_types: ListEventTypes
    list_locations: ListLocations
    list_cameras: ListCameras
    update_camera_status: UpdateCameraStatus
    list_zones: ListZones
    list_subjects: ListSubjects
