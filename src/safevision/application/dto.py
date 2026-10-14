"""Output views of the use cases. Text values are the Spanish labels of the UI.

The HTTP adapter maps these fields to the JSON keys of the public contract.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EventView:
    id: int
    type: str
    subject: str
    location: str
    camera: str
    date: str  # local date, ISO format
    time: str  # local time, HH:MM:SS
    priority: str  # Alto / Medio / Bajo
    status: str  # Pendiente / Revisado
    description: str | None


@dataclass(frozen=True)
class AlertView:
    alert_id: int
    level: str  # Alto / Medio / Bajo
    status: str  # Activa / Vista / Atendida / Descartada
    event: EventView


@dataclass(frozen=True)
class Metrics:
    total: int
    pending: int
    high: int
