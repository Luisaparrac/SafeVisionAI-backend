"""Value objects: immutable, validated on creation and compared by value.

Stored values (English) match the database; Spanish labels are what the
frontend displays.
"""

from dataclasses import dataclass
from enum import StrEnum

from safevision.domain.errors import ValidationError


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
