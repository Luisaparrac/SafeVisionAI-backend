"""Request and response bodies of the public HTTP contract.

Field names are the ones the frontend and the IoT module already use, so the
output views of the application are mapped here instead of being renamed.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from safevision.application.dto import AlertView, EventView, Metrics
from safevision.application.use_cases.register_event import RegisterEventCommand
from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone


class EventOut(BaseModel):
    """Shape of the RiskEvent used by the frontend (UI values in Spanish)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    subject: str
    location: str
    camera: str
    date: str
    time: str
    priority: str = Field(description="Alto, Medio o Bajo")
    status: str = Field(description="Pendiente o Revisado")
    description: str | None = None

    @classmethod
    def from_view(cls, view: EventView) -> "EventOut":
        return cls.model_validate(view)


class AlertOut(BaseModel):
    id_alerta: int
    nivel: str
    estado: str
    event: EventOut

    @classmethod
    def from_view(cls, view: AlertView) -> "AlertOut":
        return cls(
            id_alerta=view.alert_id,
            nivel=view.level,
            estado=view.status,
            event=EventOut.from_view(view.event),
        )


class MetricsOut(BaseModel):
    total: int
    pendientes: int
    alto: int

    @classmethod
    def from_metrics(cls, metrics: Metrics) -> "MetricsOut":
        return cls(total=metrics.total, pendientes=metrics.pending, alto=metrics.high)


class EventIn(BaseModel):
    """What the IoT module sends when it detects something."""

    camera_id: int
    event_type_id: int | None = None
    event_type: str | None = Field(None, description="Nombre del tipo, alternativa a event_type_id")
    subject_id: int | None = None
    zone_id: int | None = None
    detected_class: Literal["person", "dog", "cat", "other_animal"] = "person"
    confidence: float | None = Field(None, ge=0, le=1)
    evidence_url: str | None = None
    description: str | None = None

    def to_command(self) -> RegisterEventCommand:
        return RegisterEventCommand(**self.model_dump())


class CameraStatusIn(BaseModel):
    status: Literal["active", "inactive", "disconnected", "maintenance"]


class CameraStatusOut(BaseModel):
    camera_id: int
    status: str

    @classmethod
    def from_entity(cls, camera: Camera) -> "CameraStatusOut":
        return cls(camera_id=camera.id, status=camera.status.value)


class EventTypeOut(BaseModel):
    event_type_id: int
    name: str
    description: str | None
    severity_level: int
    priority: str

    @classmethod
    def from_entity(cls, event_type: EventType) -> "EventTypeOut":
        return cls(
            event_type_id=event_type.id,
            name=event_type.name,
            description=event_type.description,
            severity_level=event_type.severity.level,
            priority=event_type.priority.value,
        )


class LocationOut(BaseModel):
    location_id: int
    name: str
    description: str | None

    @classmethod
    def from_entity(cls, location: Location) -> "LocationOut":
        return cls(location_id=location.id, name=location.name, description=location.description)


class CameraOut(BaseModel):
    camera_id: int
    name: str
    ip_address: str
    status: str
    location_id: int

    @classmethod
    def from_entity(cls, camera: Camera) -> "CameraOut":
        return cls(
            camera_id=camera.id,
            name=camera.name,
            ip_address=str(camera.ip_address),
            status=camera.status.value,
            location_id=camera.location_id,
        )


class ZoneOut(BaseModel):
    zone_id: int
    name: str
    description: str | None
    coordinates: list[list[float]]
    is_active: bool
    camera_id: int

    @classmethod
    def from_entity(cls, zone: Zone) -> "ZoneOut":
        return cls(
            zone_id=zone.id,
            name=zone.name,
            description=zone.description,
            coordinates=zone.polygon.to_list(),
            is_active=zone.is_active,
            camera_id=zone.camera_id,
        )


class SubjectOut(BaseModel):
    subject_id: int
    name: str
    subject_type: str
    description: str | None

    @classmethod
    def from_entity(cls, subject: Subject) -> "SubjectOut":
        return cls(
            subject_id=subject.id,
            name=subject.name,
            subject_type=subject.subject_type.value,
            description=subject.description,
        )
