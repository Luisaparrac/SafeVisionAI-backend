"""Builds ``EventView`` from domain events, translating values to UI labels."""

from datetime import tzinfo

from safevision.application.dto import EventView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.errors import NotFoundError
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone


class _References:
    """Per-call cache of the catalog rows an event points to.

    Listing many events touches the same few cameras and types; each one is
    read once per call instead of once per event.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow
        self._event_types: dict[int, EventType] = {}
        self._cameras: dict[int, Camera] = {}
        self._locations: dict[int, Location] = {}
        self._subjects: dict[int, Subject | None] = {}
        self._zones: dict[int, Zone | None] = {}

    def event_type(self, event_type_id: int) -> EventType:
        if event_type_id not in self._event_types:
            found = self._uow.event_types.get(event_type_id)
            if found is None:
                raise NotFoundError("Tipo de evento", event_type_id)
            self._event_types[event_type_id] = found
        return self._event_types[event_type_id]

    def camera(self, camera_id: int) -> Camera:
        if camera_id not in self._cameras:
            found = self._uow.cameras.get(camera_id)
            if found is None:
                raise NotFoundError("Cámara", camera_id)
            self._cameras[camera_id] = found
        return self._cameras[camera_id]

    def location(self, location_id: int) -> Location:
        if location_id not in self._locations:
            found = self._uow.catalog.get_location(location_id)
            if found is None:
                raise NotFoundError("Ubicación", location_id)
            self._locations[location_id] = found
        return self._locations[location_id]

    def subject(self, subject_id: int | None) -> Subject | None:
        # Subjects and zones may have been deleted (ON DELETE SET NULL): tolerated.
        if subject_id is None:
            return None
        if subject_id not in self._subjects:
            self._subjects[subject_id] = self._uow.catalog.get_subject(subject_id)
        return self._subjects[subject_id]

    def zone(self, zone_id: int | None) -> Zone | None:
        if zone_id is None:
            return None
        if zone_id not in self._zones:
            self._zones[zone_id] = self._uow.cameras.get_zone(zone_id)
        return self._zones[zone_id]


class EventPresenter:
    def __init__(self, timezone: tzinfo) -> None:
        self._timezone = timezone

    def present(self, uow: UnitOfWork, event: Event) -> EventView:
        return self.present_many(uow, [event])[0]

    def present_many(self, uow: UnitOfWork, events: list[Event]) -> list[EventView]:
        references = _References(uow)
        return [self._view(event, references) for event in events]

    def _view(self, event: Event, references: _References) -> EventView:
        if event.id is None:
            raise ValueError("only stored events can be presented")
        event_type = references.event_type(event.event_type_id)
        camera = references.camera(event.camera_id)
        subject = references.subject(event.subject_id)
        zone = references.zone(event.zone_id)
        location = references.location(camera.location_id).name
        if zone is not None:
            location = f"{location} · {zone.name}"
        local = event.occurred_at.astimezone(self._timezone)
        return EventView(
            id=event.id,
            type=event_type.name,
            subject=subject.name
            if subject is not None
            else f"{event.detected_class.label} sin identificar",
            location=location,
            camera=camera.name,
            date=local.date().isoformat(),
            time=local.strftime("%H:%M:%S"),
            priority=event_type.priority.value,
            status=event.status.label.value,
            description=event.description,
        )
