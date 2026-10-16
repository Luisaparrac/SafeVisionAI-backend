"""Repository ports: what the application needs from persistence.

Repositories receive and return domain entities. Changes are made durable only
when the surrounding unit of work commits.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from safevision.domain.model.alert import Alert
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.values import EventStatus
from safevision.domain.model.zone import Zone


@dataclass(frozen=True)
class EventFilter:
    """Criteria to select events; ``None`` means "do not filter by this field"."""

    statuses: tuple[EventStatus, ...] | None = None
    event_type_ids: tuple[int, ...] | None = None
    camera_ids: tuple[int, ...] | None = None


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


@runtime_checkable
class EventTypeRepository(Protocol):
    """Read-only catalog of event types."""

    def get(self, event_type_id: int) -> EventType | None: ...

    def find_by_name(self, name: str) -> EventType | None:
        """Case-insensitive lookup, as the IoT module sends names."""
        ...

    def list_all(self) -> list[EventType]:
        """All types, most severe first, then by name."""
        ...


@runtime_checkable
class CameraRepository(Protocol):
    """Cameras and the zones defined on them."""

    def get(self, camera_id: int) -> Camera | None: ...

    def list_all(self) -> list[Camera]:
        """All cameras ordered by id."""
        ...

    def update(self, camera: Camera) -> None:
        """Saves the changes of an existing camera (raises NotFoundError if missing)."""
        ...

    def get_zone(self, zone_id: int) -> Zone | None: ...

    def list_zones(self) -> list[Zone]:
        """All zones ordered by id."""
        ...


@runtime_checkable
class CatalogRepository(Protocol):
    """Read-only catalogs of locations and monitored subjects."""

    def get_location(self, location_id: int) -> Location | None: ...

    def list_locations(self) -> list[Location]:
        """All locations ordered by id."""
        ...

    def get_subject(self, subject_id: int) -> Subject | None: ...

    def list_subjects(self) -> list[Subject]:
        """All subjects ordered by id."""
        ...
