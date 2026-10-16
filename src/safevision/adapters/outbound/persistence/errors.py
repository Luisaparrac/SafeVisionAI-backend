"""Translation of SQLAlchemy exceptions into application errors."""

from sqlalchemy import exc

from safevision.application.errors import (
    PersistenceError,
    StorageConflictError,
    StorageUnavailableError,
)

_UNAVAILABLE = (exc.OperationalError, exc.InterfaceError, exc.DisconnectionError, exc.TimeoutError)


def translate(error: exc.SQLAlchemyError) -> PersistenceError:
    if isinstance(error, exc.IntegrityError):
        return StorageConflictError()
    if isinstance(error, _UNAVAILABLE):
        return StorageUnavailableError()
    return PersistenceError()
