"""Creation of a panel account, when the configured registration mode allows it.

There are no roles, so an account sees every event: by default a new account
needs an invitation code. The e-mail is stored in lower case and must not belong
to anyone yet; the column is not unique, so this is the only place that keeps it so.
"""

import hmac
from dataclasses import dataclass, field

from safevision.application.dto import UserView
from safevision.application.errors import (
    EmailAlreadyRegisteredError,
    InvalidInvitationCodeError,
    RegistrationClosedError,
)
from safevision.application.ports.password_hasher import PasswordHasher
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.use_cases.authenticate_user import to_view
from safevision.domain.model.account import (
    ensure_valid_email,
    ensure_valid_name,
    ensure_valid_password,
    normalize_email,
)
from safevision.domain.model.user import User

CLOSED = "closed"
INVITE = "invite"


@dataclass(frozen=True)
class Registration:
    name: str
    email: str
    password: str = field(repr=False)
    invitation_code: str | None = field(default=None, repr=False)


class RegisterUser:
    def __init__(
        self, uow: UnitOfWork, hasher: PasswordHasher, mode: str, invitation_code: str
    ) -> None:
        self._uow = uow
        self._hasher = hasher
        self.mode = mode
        self._invitation_code = invitation_code

    def execute(self, registration: Registration) -> UserView:
        if self.mode == CLOSED:
            raise RegistrationClosedError()
        email = normalize_email(registration.email)
        ensure_valid_name(registration.name)
        ensure_valid_email(email)
        ensure_valid_password(registration.password)
        if self.mode == INVITE and not self._code_matches(registration.invitation_code):
            raise InvalidInvitationCodeError()
        self._ensure_email_is_free(email)
        # Hashed between the two transactions: it is slow on purpose and must not
        # keep a database connection busy.
        password_hash = self._hasher.hash(registration.password)
        with self._uow as uow:
            uow.users.lock_email(email)
            self._ensure_email_is_free_in(uow, email)
            user = uow.users.add(
                User(name=registration.name, email=email, password_hash=password_hash)
            )
            uow.commit()
        return to_view(user)

    def _code_matches(self, provided: str | None) -> bool:
        # Constant time, so the code cannot be guessed from how long the answer takes.
        return hmac.compare_digest((provided or "").encode(), self._invitation_code.encode())

    def _ensure_email_is_free(self, email: str) -> None:
        with self._uow as uow:
            self._ensure_email_is_free_in(uow, email)

    @staticmethod
    def _ensure_email_is_free_in(uow: UnitOfWork, email: str) -> None:
        if uow.users.find_by_email(email):
            raise EmailAlreadyRegisteredError()
