"""Password hasher port: the application never sees how passwords are stored."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        """Encoded hash of the password with a new random salt."""
        ...

    def verify(self, password: str, encoded: str) -> bool:
        """Whether the password produces ``encoded``; False for unknown formats."""
        ...
