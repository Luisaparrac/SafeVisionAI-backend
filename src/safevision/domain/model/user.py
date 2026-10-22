from dataclasses import dataclass, field

from safevision.domain.model._checks import required_id, required_text


@dataclass(kw_only=True)
class User:
    """Person who signs in to the panel.

    ``password_hash`` is the stored hash, never the password; it is left out of
    ``repr`` so it does not end up in logs or error messages.
    """

    name: str
    email: str
    password_hash: str = field(repr=False)
    id: int | None = None

    def __post_init__(self) -> None:
        self.name = required_text(self.name, "name")
        self.email = required_text(self.email, "email")
        self.password_hash = required_text(self.password_hash, "password_hash")
        self.id = None if self.id is None else required_id(self.id, "id")
