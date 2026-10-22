"""The user behind a session, read again from the database on every request.

Sessions are not stored on the server; reading the user each time is what
ends the session of someone removed from the users table.
"""

from safevision.application.dto import UserView
from safevision.application.ports.unit_of_work import UnitOfWork
from safevision.application.use_cases.authenticate_user import to_view


class GetSessionUser:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    def execute(self, user_id: int) -> UserView | None:
        """None when the user no longer exists."""
        with self._uow as uow:
            user = uow.users.get(user_id)
        return None if user is None else to_view(user)
