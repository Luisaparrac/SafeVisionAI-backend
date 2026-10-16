"""In-memory implementations of the repository ports, for tests only.

Entities are copied on the way in and out, so a use case that forgets to call
``update`` does not see its changes stored by accident.
"""

import copy

from safevision.application.ports.repositories import EventFilter
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone


class InMemoryStore[T]:
    """Rows by id with auto-increment, plus snapshot/restore for rollbacks."""

    def __init__(self, entity_name: str) -> None:
        self._entity_name = entity_name
        self._rows: dict[int, T] = {}
        self._next_id = 1

    def get(self, entity_id: int) -> T | None:
        row = self._rows.get(entity_id)
        return copy.deepcopy(row)

    def add(self, entity: T) -> T:
        stored = copy.deepcopy(entity)
        if stored.id is None:
            stored.id = self._next_id
        elif stored.id in self._rows:
            raise ValueError(f"duplicate id {stored.id}")
        self._next_id = max(self._next_id, stored.id + 1)
        self._rows[stored.id] = stored
        return copy.deepcopy(stored)

    def update(self, entity: T) -> None:
        if entity.id not in self._rows:
            raise NotFoundError(self._entity_name, entity.id)
        self._rows[entity.id] = copy.deepcopy(entity)

    def all(self) -> list[T]:
        return [copy.deepcopy(row) for _, row in sorted(self._rows.items())]

    def snapshot(self) -> tuple[dict[int, T], int]:
        return copy.deepcopy(self._rows), self._next_id

    def restore(self, state: tuple[dict[int, T], int]) -> None:
        rows, self._next_id = state
        self._rows = copy.deepcopy(rows)


class InMemoryEventRepository(InMemoryStore[Event]):
    def __init__(self) -> None:
        super().__init__("Evento")

    def find(self, criteria: EventFilter, limit: int | None = None) -> list[Event]:
        rows = [event for event in self.all() if self._matches(event, criteria)]
        rows.sort(key=lambda e: (e.occurred_at, e.id), reverse=True)
        return rows if limit is None else rows[:limit]

    def count(self, criteria: EventFilter) -> int:
        return len(self.find(criteria))

    @staticmethod
    def _matches(event: Event, criteria: EventFilter) -> bool:
        if criteria.statuses is not None and event.status not in criteria.statuses:
            return False
        if criteria.camera_ids is not None and event.camera_id not in criteria.camera_ids:
            return False
        return criteria.event_type_ids is None or event.event_type_id in criteria.event_type_ids


class InMemoryAlertRepository(InMemoryStore[Alert]):
    def __init__(self) -> None:
        super().__init__("Alerta")

    def find_by_event(self, event_id: int) -> list[Alert]:
        return [alert for alert in self.all() if alert.event_id == event_id]


class InMemoryEventTypeRepository(InMemoryStore[EventType]):
    def __init__(self) -> None:
        super().__init__("Tipo de evento")

    def find_by_name(self, name: str) -> EventType | None:
        return next((t for t in self.all() if t.has_name(name)), None)

    def list_all(self) -> list[EventType]:
        return sorted(self.all(), key=lambda t: (-t.severity.level, t.name))


class InMemoryCameraRepository(InMemoryStore[Camera]):
    def __init__(self) -> None:
        super().__init__("Cámara")
        self.zones: InMemoryStore[Zone] = InMemoryStore("Zona")

    def list_all(self) -> list[Camera]:
        return self.all()

    def get_zone(self, zone_id: int) -> Zone | None:
        return self.zones.get(zone_id)

    def list_zones(self) -> list[Zone]:
        return self.zones.all()

    def snapshot(self):
        return super().snapshot(), self.zones.snapshot()

    def restore(self, state) -> None:
        cameras, zones = state
        super().restore(cameras)
        self.zones.restore(zones)


class InMemoryCatalogRepository:
    def __init__(self) -> None:
        self.locations: InMemoryStore[Location] = InMemoryStore("Ubicación")
        self.subjects: InMemoryStore[Subject] = InMemoryStore("Sujeto")

    def get_location(self, location_id: int) -> Location | None:
        return self.locations.get(location_id)

    def list_locations(self) -> list[Location]:
        return self.locations.all()

    def get_subject(self, subject_id: int) -> Subject | None:
        return self.subjects.get(subject_id)

    def list_subjects(self) -> list[Subject]:
        return self.subjects.all()

    def snapshot(self):
        return self.locations.snapshot(), self.subjects.snapshot()

    def restore(self, state) -> None:
        locations, subjects = state
        self.locations.restore(locations)
        self.subjects.restore(subjects)
