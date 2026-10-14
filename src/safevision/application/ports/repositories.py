"""Repository ports: what the application needs from persistence.

Repositories receive and return domain entities. Changes are made durable only
when the surrounding unit of work commits.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import EventStatus


@dataclass(frozen=True)
class EventFilter:
    """Criteria to select events; ``None`` means "do not filter by this field"."""

    statuses: tuple[EventStatus, ...] | None = None
    event_type_ids: tuple[int, ...] | None = None


@runtime_checkable
class EventRepository(Protocol):
    def get(self, event_id: int) -> Event | None:
        """The event with that id, or None."""
        ...

    def add(self, event: Event) -> Event:
        """Stores a new event and returns it with its assigned id."""
        ...

    def update(self, event: Event) -> None:
        """Saves the changes of an existing event (raises NotFoundError if missing)."""
        ...

    def find(self, criteria: EventFilter, limit: int | None = None) -> list[Event]:
        """Matching events, newest first (by occurrence time, then by id)."""
        ...

    def count(self, criteria: EventFilter) -> int:
        """Number of matching events."""
        ...


@runtime_checkable
class AlertRepository(Protocol):
    def get(self, alert_id: int) -> Alert | None:
        """The alert with that id, or None."""
        ...

    def add(self, alert: Alert) -> Alert:
        """Stores a new alert and returns it with its assigned id."""
        ...

    def update(self, alert: Alert) -> None:
        """Saves the changes of an existing alert (raises NotFoundError if missing)."""
        ...

    def find_by_event(self, event_id: int) -> list[Alert]:
        """Alerts raised for an event, oldest first (by id)."""
        ...
