"""Event history with the filters of the panel: text, priority, status, camera and dates."""

from datetime import date, datetime, time, timedelta

from safevision.application.dto import EventView
from safevision.application.ports.repositories import EventFilter
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.presenter import EventPresenter
from safevision.domain.errors import ValidationError
from safevision.domain.model.values import Priority, ReviewLabel


class ListEvents:
    def __init__(self, uow: UnitOfWork, presenter: EventPresenter) -> None:
        self._uow = uow
        self._presenter = presenter

    def execute(
        self,
        q: str | None = None,
        priority: str | None = None,
        status: str | None = None,
        camera_id: int | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[EventView]:
        """Newest first. Unknown priority or status labels are ignored, as in the panel.

        ``q`` matches, case-insensitively, the id, type, subject or location shown.
        ``camera_id`` keeps only the events of that camera. ``date_from`` and
        ``date_to`` are local dates in the configured time zone, both inclusive.
        ``offset`` and ``limit`` page the filtered result; without them nothing is cut.
        """
        if date_from is not None and date_to is not None and date_from > date_to:
            raise ValidationError("La fecha 'desde' no puede ser posterior a 'hasta'")
        with self._uow as uow:
            criteria = EventFilter(
                statuses=self._statuses(status),
                event_type_ids=self._event_type_ids(uow, priority),
                camera_ids=None if camera_id is None else (camera_id,),
                occurred_from=self._start_of(date_from),
                occurred_before=self._start_of(date_to + timedelta(days=1) if date_to else None),
            )
            if not q:
                # Paged by the repository: only the requested page is read and presented.
                events = uow.events.find(criteria, limit=limit, offset=offset)
                return self._presenter.present_many(uow, events)
            views = self._presenter.present_many(uow, uow.events.find(criteria))
        # The text search runs on the presented values, so the page is cut afterwards.
        term = q.lower().strip()
        views = [
            view
            for view in views
            if any(
                term in str(value).lower()
                for value in (view.id, view.type, view.subject, view.location)
            )
        ]
        return views[offset:] if limit is None else views[offset : offset + limit]

    def _start_of(self, day: date | None) -> datetime | None:
        if day is None:
            return None
        return datetime.combine(day, time.min, tzinfo=self._presenter.timezone)

    @staticmethod
    def _statuses(label: str | None):
        if label is None:
            return None
        try:
            return ReviewLabel.parse(label).statuses
        except ValidationError:
            return None

    @staticmethod
    def _event_type_ids(uow: UnitOfWork, label: str | None) -> tuple[int, ...] | None:
        if label is None:
            return None
        try:
            levels = Priority.parse(label).severity_levels
        except ValidationError:
            return None
        return tuple(t.id for t in uow.event_types.list_all() if t.severity.level in levels)
