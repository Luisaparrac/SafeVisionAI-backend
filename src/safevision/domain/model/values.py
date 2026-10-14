"""Value objects: immutable, validated on creation and compared by value.

Stored values (English) match the database; Spanish labels are what the
frontend displays.
"""

from dataclasses import dataclass
from enum import StrEnum

from safevision.domain.errors import InvalidTransitionError, ValidationError


class _ParsableEnum(StrEnum):
    """String enum whose ``parse`` raises a domain error instead of ``ValueError``."""

    @classmethod
    def parse(cls, value: str):
        try:
            return cls(value)
        except ValueError:
            raise ValidationError(f"Valor inválido para {cls.__name__}: {value!r}") from None


class Priority(StrEnum):
    """The three priority levels displayed by the frontend."""

    HIGH = "Alto"
    MEDIUM = "Medio"
    LOW = "Bajo"

    @classmethod
    def parse(cls, label: str) -> "Priority":
        try:
            return cls(label)
        except ValueError:
            raise ValidationError(f"Prioridad inválida: {label!r}") from None

    @property
    def severity_levels(self) -> tuple[int, ...]:
        """Severity levels grouped under this priority."""
        return _LEVELS_BY_PRIORITY[self]


_LEVELS_BY_PRIORITY = {
    Priority.HIGH: (3, 4),
    Priority.MEDIUM: (2,),
    Priority.LOW: (1,),
}


@dataclass(frozen=True, order=True)
class Severity:
    """Severity of an event type or alert level, from 1 (lowest) to 4 (highest)."""

    level: int

    MIN = 1
    MAX = 4

    def __post_init__(self) -> None:
        if isinstance(self.level, bool) or not isinstance(self.level, int):
            raise ValidationError(f"La severidad debe ser un entero, no {self.level!r}")
        if not self.MIN <= self.level <= self.MAX:
            raise ValidationError(
                f"La severidad debe estar entre {self.MIN} y {self.MAX}, no {self.level}"
            )

    @property
    def priority(self) -> Priority:
        """Severity 3-4 is high, 2 is medium and 1 is low."""
        if self.level >= 3:
            return Priority.HIGH
        return Priority.MEDIUM if self.level == 2 else Priority.LOW


class ReviewLabel(StrEnum):
    """How the frontend groups event statuses."""

    PENDING = "Pendiente"
    REVIEWED = "Revisado"

    @classmethod
    def parse(cls, label: str) -> "ReviewLabel":
        try:
            return cls(label)
        except ValueError:
            raise ValidationError(f"Estado inválido: {label!r}") from None

    @property
    def statuses(self) -> tuple["EventStatus", ...]:
        """Event statuses displayed under this label."""
        return tuple(status for status in EventStatus if status.label is self)


class EventStatus(_ParsableEnum):
    """Life cycle of an event.

    pending -> in_review -> resolved | false_alarm
    pending -> resolved | false_alarm
    resolved and false_alarm are terminal.
    """

    PENDING = "pending"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    FALSE_ALARM = "false_alarm"

    @property
    def is_open(self) -> bool:
        return self in (EventStatus.PENDING, EventStatus.IN_REVIEW)

    @property
    def label(self) -> ReviewLabel:
        return ReviewLabel.PENDING if self.is_open else ReviewLabel.REVIEWED

    def can_transition_to(self, target: "EventStatus") -> bool:
        return target in _EVENT_TRANSITIONS[self]

    def transition_to(self, target: "EventStatus") -> "EventStatus":
        if not self.can_transition_to(target):
            raise InvalidTransitionError("Evento", self.value, target.value)
        return target


_EVENT_TRANSITIONS = {
    EventStatus.PENDING: frozenset(
        {EventStatus.IN_REVIEW, EventStatus.RESOLVED, EventStatus.FALSE_ALARM}
    ),
    EventStatus.IN_REVIEW: frozenset({EventStatus.RESOLVED, EventStatus.FALSE_ALARM}),
    EventStatus.RESOLVED: frozenset(),
    EventStatus.FALSE_ALARM: frozenset(),
}


class AlertStatus(_ParsableEnum):
    """Life cycle of an alert.

    active -> seen -> resolved | dismissed
    active -> resolved | dismissed
    resolved and dismissed are terminal and require an attention time.
    """

    ACTIVE = "active"
    SEEN = "seen"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"

    @property
    def is_open(self) -> bool:
        return self in (AlertStatus.ACTIVE, AlertStatus.SEEN)

    @property
    def label(self) -> str:
        return _ALERT_LABELS[self]

    def can_transition_to(self, target: "AlertStatus") -> bool:
        return target in _ALERT_TRANSITIONS[self]

    def transition_to(self, target: "AlertStatus") -> "AlertStatus":
        if not self.can_transition_to(target):
            raise InvalidTransitionError("Alerta", self.value, target.value)
        return target


_ALERT_LABELS = {
    AlertStatus.ACTIVE: "Activa",
    AlertStatus.SEEN: "Vista",
    AlertStatus.RESOLVED: "Atendida",
    AlertStatus.DISMISSED: "Descartada",
}

_ALERT_TRANSITIONS = {
    AlertStatus.ACTIVE: frozenset({AlertStatus.SEEN, AlertStatus.RESOLVED, AlertStatus.DISMISSED}),
    AlertStatus.SEEN: frozenset({AlertStatus.RESOLVED, AlertStatus.DISMISSED}),
    AlertStatus.RESOLVED: frozenset(),
    AlertStatus.DISMISSED: frozenset(),
}


class DetectedClass(_ParsableEnum):
    """What the IoT vision model detected."""

    PERSON = "person"
    DOG = "dog"
    CAT = "cat"
    OTHER_ANIMAL = "other_animal"

    @property
    def label(self) -> str:
        return _CLASS_LABELS[self]


_CLASS_LABELS = {
    DetectedClass.PERSON: "Persona",
    DetectedClass.DOG: "Perro",
    DetectedClass.CAT: "Gato",
    DetectedClass.OTHER_ANIMAL: "Animal",
}


class CameraStatus(_ParsableEnum):
    """Operational status reported for a camera."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONNECTED = "disconnected"
    MAINTENANCE = "maintenance"

    @property
    def is_operational(self) -> bool:
        return self is CameraStatus.ACTIVE
