"""Port of the password reset links: signed values, since there is no table to store them."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ResetTicket:
    user_id: int
    fingerprint: str = field(repr=False)


@runtime_checkable
class PasswordResetTokens(Protocol):
    def issue(self, user_id: int, fingerprint: str) -> str:
        """Value for the link; ``fingerprint`` ties it to the current password."""
        ...

    def read(self, token: str) -> ResetTicket | None:
        """What a valid, unexpired token says; None for anything else."""
        ...
