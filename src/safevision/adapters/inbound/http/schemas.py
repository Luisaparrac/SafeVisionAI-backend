"""Request and response bodies of the public HTTP contract.

Field names are the ones the frontend and the IoT module already use, so the
output views of the application are mapped here instead of being renamed.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from safevision.application.dto import (
    AlertView,
    EventView,
    InstallationNodeView,
    InstallationsView,
    Metrics,
    UserView,
)
from safevision.application.use_cases.register_event import RegisterEventCommand
from safevision.application.use_cases.register_user import Registration
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
    occurred_at: str = Field(description="Instante ISO 8601 con zona, en TIMEZONE")
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


# The columns have no limit; these keep one request from storing arbitrary amounts of text.
MAX_DESCRIPTION_LENGTH = 2000
MAX_EVIDENCE_URL_LENGTH = 2048


class EventIn(BaseModel):
    """What the IoT module sends when it detects something."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "camera_id": 1,
                    "event_type": "Fall",
                    "subject_id": 1,
                    "zone_id": 1,
                    "detected_class": "person",
                    "confidence": 0.92,
                    "evidence_url": "https://example.com/evidencias/0001.jpg",
                    "description": "Persona en el piso junto a la escalera",
                },
                {"camera_id": 2, "event_type_id": 3, "detected_class": "dog"},
            ]
        }
    )

    camera_id: int
    event_type_id: int | None = None
    event_type: str | None = Field(
        None,
        description="Nombre del tipo como en /api/tipos-evento; alternativa a event_type_id",
    )
    subject_id: int | None = None
    zone_id: int | None = None
    detected_class: Literal["person", "dog", "cat", "other_animal"] = "person"
    confidence: float | None = Field(None, ge=0, le=1)
    evidence_url: str | None = Field(None, max_length=MAX_EVIDENCE_URL_LENGTH)
    description: str | None = Field(None, max_length=MAX_DESCRIPTION_LENGTH)

    def to_command(self) -> RegisterEventCommand:
        return RegisterEventCommand(**self.model_dump())


class CameraStatusIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "disconnected"}]})

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


class EventTypeCountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type_id: int
    name: str
    priority: str
    total: int


class CameraCountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    camera_id: int
    name: str
    total: int


def _pending_summary(view: InstallationNodeView) -> dict[str, int | str | None]:
    return {
        "own_pending": view.own_pending,
        "pending": view.pending,
        "max_severity": view.max_severity,
        "priority": view.priority,
    }


class InstallationZoneOut(BaseModel):
    zone_id: int
    name: str
    own_pending: int
    pending: int
    max_severity: int | None
    priority: str | None

    @classmethod
    def from_view(cls, view: InstallationNodeView) -> "InstallationZoneOut":
        return cls(zone_id=view.id, name=view.name, **_pending_summary(view))


class InstallationCameraOut(BaseModel):
    camera_id: int
    name: str
    status: str
    own_pending: int = Field(description="Pendientes de la cámara que no están en ninguna zona")
    pending: int = Field(description="Pendientes de la cámara y de sus zonas")
    max_severity: int | None
    priority: str | None
    zones: list[InstallationZoneOut]

    @classmethod
    def from_view(cls, view: InstallationNodeView) -> "InstallationCameraOut":
        return cls(
            camera_id=view.id,
            name=view.name,
            status=view.status,
            zones=[InstallationZoneOut.from_view(zone) for zone in view.children],
            **_pending_summary(view),
        )


class InstallationLocationOut(BaseModel):
    location_id: int
    name: str
    own_pending: int
    pending: int = Field(description="Pendientes de todas las cámaras y zonas de la ubicación")
    max_severity: int | None = Field(description="De 1 a 4; null si no hay pendientes")
    priority: str | None = Field(description="Alto, Medio o Bajo; null si no hay pendientes")
    cameras: list[InstallationCameraOut]

    @classmethod
    def from_view(cls, view: InstallationNodeView) -> "InstallationLocationOut":
        return cls(
            location_id=view.id,
            name=view.name,
            cameras=[InstallationCameraOut.from_view(camera) for camera in view.children],
            **_pending_summary(view),
        )


class InstallationsOut(BaseModel):
    pending: int
    max_severity: int | None
    priority: str | None
    locations: list[InstallationLocationOut]

    @classmethod
    def from_view(cls, view: InstallationsView) -> "InstallationsOut":
        return cls(
            pending=view.pending,
            max_severity=view.max_severity,
            priority=view.priority,
            locations=[InstallationLocationOut.from_view(item) for item in view.locations],
        )


# RFC 5321 limit for an address; passwords are capped so one request cannot hash megabytes.
MAX_EMAIL_LENGTH = 320
MAX_PASSWORD_LENGTH = 1024


class LoginIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "usuario@example.com", "password": "contraseña"}]}
    )

    email: str = Field(max_length=MAX_EMAIL_LENGTH)
    password: str = Field(max_length=MAX_PASSWORD_LENGTH)


class RegisterIn(BaseModel):
    """Lengths and formats are rules of the domain, so they answer with its messages."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Usuario de ejemplo",
                    "email": "usuario@example.com",
                    "password": "contraseña1",
                    "invitation_code": "código",
                }
            ]
        }
    )

    name: str
    email: str
    password: str
    invitation_code: str | None = None

    def to_registration(self) -> Registration:
        return Registration(**self.model_dump())


class ForgotPasswordIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"email": "usuario@example.com"}]})

    email: str = Field(max_length=MAX_EMAIL_LENGTH)


class ResetPasswordIn(BaseModel):
    """The password has no limit here so that the policy answers with its own message."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"token": "<token>", "new_password": "contraseña1"}]}
    )

    token: str
    new_password: str


class AuthOptionsOut(BaseModel):
    """What the panel may offer; lets it show or hide its buttons."""

    registration: Literal["closed", "invite", "open"]
    password_recovery: bool


class MessageOut(BaseModel):
    detail: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str


class SessionOut(BaseModel):
    """Answer of login and of the current session; the frontend reads ``authenticated``."""

    authenticated: bool = True
    user: UserOut

    @classmethod
    def from_view(cls, view: UserView) -> "SessionOut":
        return cls(user=UserOut(id=view.id, name=view.name, email=view.email))


class WsTicketOut(BaseModel):
    ticket: str = Field(description="Se envía como /ws/alertas?ticket=...")
    expires_in: int = Field(description="Segundos de validez")
