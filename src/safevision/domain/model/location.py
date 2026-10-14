from dataclasses import dataclass

from safevision.domain.model._checks import optional_text, required_id, required_text


@dataclass(kw_only=True)
class Location:
    """Monitored place (a house, a room) owned by a user."""

    name: str
    user_id: int
    description: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        self.user_id = required_id(self.user_id, "user_id")
        self.description = optional_text(self.description, "description")
        self.id = None if self.id is None else required_id(self.id, "id")
