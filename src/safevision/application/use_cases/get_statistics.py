"""Event counts per type and per camera, optionally between two local dates."""

from datetime import date, tzinfo

from safevision.application.date_range import local_day_range
from safevision.application.dto import CameraCount, EventTypeCount
from safevision.application.ports.repositories import EventFilter
from safevision.application.ports.unit_of_work import UnitOfWork


class _Statistics:
    def __init__(self, uow: UnitOfWork, timezone: tzinfo) -> None:
        self._uow = uow
        self._timezone = timezone

    def _criteria(self, date_from: date | None, date_to: date | None) -> EventFilter:
        start, end = local_day_range(date_from, date_to, self._timezone)
        return EventFilter(occurred_from=start, occurred_before=end)


class GetEventTypeStatistics(_Statistics):
    def execute(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> list[EventTypeCount]:
        """Every event type, also those without events; most frequent first, then by name."""
        criteria = self._criteria(date_from, date_to)
        with self._uow as uow:
            counts = uow.events.count_by_event_type(criteria)
            types = uow.event_types.list_all()
        rows = [EventTypeCount(t.id, t.name, t.priority.value, counts.get(t.id, 0)) for t in types]
        return sorted(rows, key=lambda row: (-row.total, row.name))


class GetCameraStatistics(_Statistics):
    def execute(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> list[CameraCount]:
        """Every camera, also those without events; most frequent first, then by id."""
        criteria = self._criteria(date_from, date_to)
        with self._uow as uow:
            counts = uow.events.count_by_camera(criteria)
            cameras = uow.cameras.list_all()
        rows = [CameraCount(c.id, c.name, counts.get(c.id, 0)) for c in cameras]
        return sorted(rows, key=lambda row: (-row.total, row.camera_id))
