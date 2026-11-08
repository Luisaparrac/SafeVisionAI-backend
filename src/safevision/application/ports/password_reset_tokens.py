"""Port of the password reset links: signed values, since there is no table to store them."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordResetTokens(Protocol):
    def issue(self, user_id: int, fingerprint: str) -> str:
        """Value for the link; ``fingerprint`` ties it to the current password."""
        ...
