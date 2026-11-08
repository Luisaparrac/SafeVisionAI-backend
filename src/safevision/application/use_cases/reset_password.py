"""Sets a new password from the link of the recovery e-mail.

The link is bound to the current password through its fingerprint: once the
password changes the same link no longer matches, so it works only once and
needs no table. Changing the password also ends the sessions opened with the
old one. It does not open a session.
"""

from safevision.application.errors import InvalidResetTokenError, TooManyRequestsError
from safevision.application.ports.password_hasher import PasswordHasher
from safevision.application.ports.password_reset_tokens import PasswordResetTokens
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.services.rate_limiter import SlidingWindowLimiter
from safevision.domain.model.account import ensure_valid_password


class ResetPassword:
    def __init__(
        self,
        uow: UnitOfWork,
        hasher: PasswordHasher,
        tokens: PasswordResetTokens,
        per_client: SlidingWindowLimiter,
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self._tokens = tokens
        self._per_client = per_client

    def execute(self, token: str, new_password: str, client: str) -> None:
        """``client`` is only a key in memory for the limit: never stored or logged."""
        if not self._per_client.try_acquire(client):
            raise TooManyRequestsError()
        ticket = self._tokens.read(token)
        if ticket is None:
            raise InvalidResetTokenError()
        with self._uow as uow:
            user = uow.users.get(ticket.user_id)
        if user is None or not user.matches_fingerprint(ticket.fingerprint):
            raise InvalidResetTokenError()
        # After the link: a weak password does not spend it, and can be corrected.
        ensure_valid_password(new_password)
        # Hashed outside the transaction: it is slow on purpose.
        new_hash = self._hasher.hash(new_password)
        with self._uow as uow:
            changed = uow.users.replace_password_hash(ticket.user_id, user.password_hash, new_hash)
            uow.commit()
        if not changed:  # another request with the same link got there first
            raise InvalidResetTokenError()
