from dataclasses import dataclass
from datetime import datetime

from safevision.domain.errors import ValidationError
from safevision.domain.model._checks import aware_datetime, optional_id, optional_text, required_id
from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.values import Confidence, DetectedClass, EventStatus
from safevision.domain.model.zone import Zone


@dataclass(kw_only=True)
class Event:
    """Risk situation detected by a camera."""

    camera_id: int
    event_type_id: int
    occurred_at: datetime
    status: EventStatus = EventStatus.PENDING
    detected_class: DetectedClass = DetectedClass.PERSON
    confidence: Confidence | None = None
    evidence_url: str | None = None
    description: str | None = None
    subject_id: int | None = None
    zone_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.camera_id = required_id(self.camera_id, "camera_id")
        self.event_type_id = required_id(self.event_type_id, "event_type_id")
        self.occurred_at = aware_datetime(self.occurred_at, "occurred_at")
        if isinstance(self.status, str):
            self.status = EventStatus.parse(self.status)
        if isinstance(self.detected_class, str):
            self.detected_class = DetectedClass.parse(self.detected_class)
        if self.confidence is not None and not isinstance(self.confidence, Confidence):
            self.confidence = Confidence(self.confidence)
        self.evidence_url = optional_text(self.evidence_url, "evidence_url")
        self.description = optional_text(self.description, "description")
        self.subject_id = optional_id(self.subject_id, "subject_id")
        self.zone_id = optional_id(self.zone_id, "zone_id")
        self.id = None if self.id is None else required_id(self.id, "id")

    @classmethod
    def register(
        cls,
        *,
        camera: Camera,
        event_type: EventType,
        occurred_at: datetime,
        zone: Zone | None = None,
        **details,
    ) -> "Event":
        """Creates a new pending event; the zone, if any, must belong to the camera."""
        if camera.id is None or event_type.id is None:
            raise ValidationError("La cámara y el tipo de evento deben estar registrados")
        if zone is not None and not zone.belongs_to(camera.id):
            raise ValidationError(f"La zona {zone.id} no pertenece a la cámara {camera.id}")
        return cls(
            camera_id=camera.id,
            event_type_id=event_type.id,
            occurred_at=occurred_at,
            zone_id=None if zone is None else zone.id,
            **details,
        )

    @property
    def is_open(self) -> bool:
        return self.status.is_open

    def resolve(self) -> None:
        self.status = self.status.transition_to(EventStatus.RESOLVED)

    def mark_false_alarm(self) -> None:
        self.status = self.status.transition_to(EventStatus.FALSE_ALARM)
