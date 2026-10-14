from dataclasses import dataclass
from datetime import datetime

from safevision.domain.errors import ValidationError
from safevision.domain.model._checks import aware_datetime, optional_id, required_id
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.values import AlertStatus, Severity


@dataclass(kw_only=True)
class Alert:
    """Notification raised for an event; its level is the event type severity."""

    event_id: int
    level: Severity
    created_at: datetime
    status: AlertStatus = AlertStatus.ACTIVE
    attended_at: datetime | None = None
    attended_by_user_id: int | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.event_id = required_id(self.event_id, "event_id")
        if isinstance(self.level, int):
            self.level = Severity(self.level)
        self.created_at = aware_datetime(self.created_at, "created_at")
        if isinstance(self.status, str):
            self.status = AlertStatus.parse(self.status)
        if self.attended_at is not None:
            self.attended_at = self._attention_time(self.attended_at)
        elif not self.status.is_open:
            raise ValidationError("Una alerta cerrada debe tener fecha de atención")
        self.attended_by_user_id = optional_id(self.attended_by_user_id, "attended_by_user_id")
        self.id = None if self.id is None else required_id(self.id, "id")

    @classmethod
    def for_event(cls, event: Event, event_type: EventType) -> "Alert":
        if event.id is None:
            raise ValidationError("El evento debe estar registrado antes de crear su alerta")
        return cls(event_id=event.id, level=event_type.severity, created_at=event.occurred_at)

    @property
    def is_open(self) -> bool:
        return self.status.is_open

    def mark_seen(self) -> None:
        self.status = self.status.transition_to(AlertStatus.SEEN)

    def close(self, at: datetime, by_user_id: int | None = None) -> None:
        """The alert was attended: the situation was handled."""
        self._finish(AlertStatus.RESOLVED, at, by_user_id)

    def dismiss(self, at: datetime, by_user_id: int | None = None) -> None:
        """The alert was discarded without action."""
        self._finish(AlertStatus.DISMISSED, at, by_user_id)

    def _finish(self, target: AlertStatus, at: datetime, by_user_id: int | None) -> None:
        # Validate everything first so a failure leaves the alert unchanged.
        status = self.status.transition_to(target)
        attended_at = self._attention_time(at)
        attended_by = optional_id(by_user_id, "attended_by_user_id")
        self.status, self.attended_at, self.attended_by_user_id = status, attended_at, attended_by

    def _attention_time(self, at: datetime) -> datetime:
        at = aware_datetime(at, "attended_at")
        if at < self.created_at:
            raise ValidationError("La fecha de atención no puede ser anterior a la de creación")
        return at
