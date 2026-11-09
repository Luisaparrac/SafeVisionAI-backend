import hashlib
import hmac
from dataclasses import dataclass, field

from safevision.domain.model._checks import required_id, required_text

FINGERPRINT_LENGTH = 16


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

    @property
    def password_fingerprint(self) -> str:
        """Short value derived from the stored hash, carried by the signed tokens.

        It changes with the password, which is what invalidates the sessions and
        reset links issued before. The hash includes a random salt, so nothing
        about the password can be guessed from it.
        """
        return hashlib.sha256(self.password_hash.encode()).hexdigest()[:FINGERPRINT_LENGTH]

    def matches_fingerprint(self, fingerprint: str) -> bool:
        return hmac.compare_digest(self.password_fingerprint.encode(), fingerprint.encode())
