from dataclasses import dataclass

from safevision.domain.model._checks import optional_text, required_id, required_text
from safevision.domain.model.values import SubjectType


@dataclass(kw_only=True)
class Subject:
    """Monitored person or pet registered by a user."""

    name: str
    subject_type: SubjectType
    user_id: int
    description: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        if isinstance(self.subject_type, str):
            self.subject_type = SubjectType.parse(self.subject_type)
        self.user_id = required_id(self.user_id, "user_id")
        self.description = optional_text(self.description, "description")
        self.id = None if self.id is None else required_id(self.id, "id")
