from dataclasses import dataclass, field
from datetime import datetime

from safevision.domain.model._checks import aware_datetime, required_id, required_text
from safevision.domain.model.values import Email


@dataclass(kw_only=True)
class User:
    """Person who uses the monitoring panel."""

    name: str
    email: Email
    password_hash: str = field(repr=False)
    created_at: datetime | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        if isinstance(self.email, str):
            self.email = Email(self.email)
        self.password_hash = required_text(self.password_hash, "password_hash")
        if self.created_at is not None:
            self.created_at = aware_datetime(self.created_at, "created_at")
        self.id = None if self.id is None else required_id(self.id, "id")
