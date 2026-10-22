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
    occurred_at: str  # ISO 8601 instant with the offset of the local time zone
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


NEW_ALERT = "new_alert"
EVENT_CLOSED = "event_closed"


@dataclass(frozen=True)
class AlertNotification:
    """Something the panel should hear about right away.

    ``new_alert``: an event was registered and raised ``alert``.
    ``event_closed``: ``event`` was reviewed or marked as a false alarm.
    """

    kind: str
    event: EventView
    alert: AlertView | None = None


@dataclass(frozen=True)
class EventTypeCount:
    event_type_id: int
    name: str
    priority: str  # Alto / Medio / Bajo
    total: int


@dataclass(frozen=True)
class CameraCount:
    camera_id: int
    name: str
    total: int
