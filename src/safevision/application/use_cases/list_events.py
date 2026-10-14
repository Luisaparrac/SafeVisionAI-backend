"""Event history with the filters of the panel: text, priority and status."""

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
        self, q: str | None = None, priority: str | None = None, status: str | None = None
    ) -> list[EventView]:
        """Newest first. Unknown priority or status labels are ignored, as in the panel.

        ``q`` matches, case-insensitively, the id, type, subject or location shown.
        """
        with self._uow as uow:
            criteria = EventFilter(
                statuses=self._statuses(status),
                event_type_ids=self._event_type_ids(uow, priority),
            )
            views = self._presenter.present_many(uow, uow.events.find(criteria))
        if q:
            term = q.lower().strip()
            views = [
                view
                for view in views
                if any(
                    term in str(value).lower()
                    for value in (view.id, view.type, view.subject, view.location)
                )
            ]
        return views

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
