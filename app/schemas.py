from typing import Literal

from pydantic import BaseModel, Field


class EventView(BaseModel):
    """Exactly the shape the frontend's RiskEvent uses (UI values in Spanish)."""
    id: int
    type: str
    subject: str
    location: str
    camera: str
    date: str
    time: str
    priority: str   # Alto / Medio / Bajo
    status: str     # Pendiente / Revisado
    description: str | None = None


class AlertView(BaseModel):
    id_alerta: int
    nivel: str
    estado: str
    event: EventView


class EventCreate(BaseModel):
    """What the IoT module sends when it detects something."""
    camera_id: int
    event_type_id: int | None = None
    event_type: str | None = Field(None, description="Event type name, alternative to event_type_id")
    subject_id: int | None = None
    zone_id: int | None = None
    detected_class: Literal["person", "dog", "cat", "other_animal"] = "person"
    confidence: float | None = Field(None, ge=0, le=1)
    evidence_url: str | None = None
    description: str | None = None


class Metrics(BaseModel):
    total: int
    pendientes: int
    alto: int


class CameraStatus(BaseModel):
    status: Literal["active", "inactive", "disconnected", "maintenance"]
