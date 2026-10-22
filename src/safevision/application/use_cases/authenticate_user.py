"""Login of the panel: e-mail and password checked against the users table.

The e-mail is compared in lower case and must belong to exactly one user,
because the column is not unique. Every failure raises the same error and,
when no user matches, the password is still checked against a throwaway hash,
so neither the message nor the response time tells whether the e-mail exists.
"""

import secrets

from safevision.application.dto import UserView
from safevision.application.errors import InvalidCredentialsError
from safevision.application.ports.password_hasher import PasswordHasher
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.domain.model.identity import require_id
from safevision.domain.model.user import User


class AuthenticateUser:
    def __init__(self, uow: UnitOfWork, hasher: PasswordHasher) -> None:
        self._uow = uow
        self._hasher = hasher
        self._dummy_hash: str | None = None

    def execute(self, email: str, password: str) -> UserView:
        with self._uow as uow:
            matches = uow.users.find_by_email(email.strip().lower())
        # The hash is checked after the transaction: it is slow on purpose and
        # must not keep a database connection busy.
        user = matches[0] if len(matches) == 1 else None
        encoded = user.password_hash if user is not None else self._throwaway_hash()
        if not self._hasher.verify(password, encoded) or user is None:
            raise InvalidCredentialsError()
        return to_view(user)

    def _throwaway_hash(self) -> str:
        # Built on first use, so creating the use case stays fast.
        if self._dummy_hash is None:
            self._dummy_hash = self._hasher.hash(secrets.token_urlsafe(16))
        return self._dummy_hash


def to_view(user: User) -> UserView:
    return UserView(id=require_id(user.id), name=user.name, email=user.email)
