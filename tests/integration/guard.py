"""Safety check that runs before any DDL against the integration test database.

The integration fixtures drop and recreate tables. They may only do that on a
local, disposable database, so TEST_DATABASE_URL must point to localhost and to
a database whose name ends in "_test". Error messages never include the URL,
because it may contain a password.
"""

from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

SAFE_HOSTS = frozenset({"localhost", "127.0.0.1"})
# libpq query parameters that would redirect the connection to another server.
_REDIRECTING_PARAMS = frozenset({"host", "hostaddr", "service"})


class UnsafeTestDatabaseError(RuntimeError):
    pass


def ensure_safe_test_database(url: str) -> None:
    """Raises UnsafeTestDatabaseError unless the URL is a local "*_test" PostgreSQL database."""
    try:
        parsed = make_url(url)
    except ArgumentError:
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL no es una URL válida") from None
    if not parsed.drivername.startswith("postgres"):
        raise UnsafeTestDatabaseError("TEST_DATABASE_URL debe apuntar a PostgreSQL")
    if parsed.host not in SAFE_HOSTS or _REDIRECTING_PARAMS & set(parsed.query):
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL debe usar el host localhost o 127.0.0.1; no se ejecutó nada"
        )
    if not (parsed.database or "").endswith("_test"):
        raise UnsafeTestDatabaseError(
            'El nombre de la base de TEST_DATABASE_URL debe terminar en "_test"; no se ejecutó nada'
        )
