"""Infrastructure failures as the application sees them.

Adapters translate their own exceptions into these, so the messages are safe
to show: they never include SQL, parameters, hosts or users.
"""


class PersistenceError(Exception):
    """The data could not be read or written."""

    default_message = "Error al acceder a los datos"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.default_message
        super().__init__(self.message)


class StorageUnavailableError(PersistenceError):
    """The database cannot be reached right now; retrying later may work."""

    default_message = "La base de datos no está disponible. Intenta de nuevo más tarde."


class StorageConflictError(PersistenceError):
    """The change contradicts data stored meanwhile (for example a deleted reference)."""

    default_message = "Los datos cambiaron mientras se procesaba la petición. Intenta de nuevo."


class InvalidCredentialsError(Exception):
    """Login refused. The message is the same whether the e-mail or the password failed."""

    message = "Correo o contraseña incorrectos"

    def __init__(self) -> None:
        super().__init__(self.message)
