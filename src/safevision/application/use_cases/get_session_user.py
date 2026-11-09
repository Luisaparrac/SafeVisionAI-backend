"""The user behind a session, read again from the database on every request.

Sessions are not stored on the server; reading the user each time is what
ends the session of someone removed from the users table or whose password
changed after the session started.
"""

from safevision.application.dto import UserView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.use_cases.authenticate_user import to_view


class GetSessionUser:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: int, fingerprint: str) -> UserView | None:
        """None when the user no longer exists or has another password now."""
        with self._uow as uow:
            user = uow.users.get(user_id)
        return None if user is None or not user.matches_fingerprint(fingerprint) else to_view(user)
