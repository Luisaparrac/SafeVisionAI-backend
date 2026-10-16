import pytest
from sqlalchemy import exc

from safevision.adapters.outbound.persistence.errors import translate
from safevision.application.errors import (
    PersistenceError,
    StorageConflictError,
    StorageUnavailableError,
)


def dbapi(cls, detail="password=s3cret host=db.example.com"):
    return cls("INSERT INTO events VALUES (%(x)s)", {"x": "dato"}, Exception(detail))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (dbapi(exc.IntegrityError), StorageConflictError),
        (dbapi(exc.OperationalError), StorageUnavailableError),
        (dbapi(exc.InterfaceError), StorageUnavailableError),
        (exc.TimeoutError("pool exhausted"), StorageUnavailableError),
        (dbapi(exc.ProgrammingError), PersistenceError),
    ],
)
def test_translation(error, expected):
    translated = translate(error)
    assert type(translated) is expected
    assert "s3cret" not in translated.message
    assert "INSERT" not in translated.message
