from dataclasses import dataclass

from safevision.domain.model._checks import optional_text, required_text
from safevision.domain.model.values import Priority, Severity


@dataclass(kw_only=True)
class EventType:
    """Kind of risk event (for example a fall), with its severity."""

    name: str
    severity: Severity
    description: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        self.description = optional_text(self.description, "description")
        if isinstance(self.severity, int):
            self.severity = Severity(self.severity)

    @property
    def priority(self) -> Priority:
        return self.severity.priority
