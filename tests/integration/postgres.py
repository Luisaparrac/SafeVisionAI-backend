"""PostgreSQL fixtures for integration and contract tests (pytest plugin).

They use only TEST_DATABASE_URL; without it the tests that need a database are
skipped, or fail when REQUIRE_TEST_DATABASE=1 (as in CI). Before any DDL the
guard checks that the URL is a local "*_test" database. Then the tables of
schema.sql are dropped and recreated once per session, and emptied before each
test so identifiers always start at 1.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.database import make_engine
from safevision.adapters.outbound.persistence.orm import (
    CameraRow,
    EventTypeRow,
    LocationRow,
    SubjectRow,
    UserRow,
    ZoneRow,
)
from tests.fakes.users import TEST_EMAIL, TEST_NAME, TEST_PASSWORD_HASH
from tests.integration.guard import UnsafeTestDatabaseError, ensure_safe_test_database

SCHEMA = Path(__file__).with_name("schema.sql")
TABLES = ("alerts", "events", "event_types", "subjects", "zones", "cameras", "locations", "users")
SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]


def sql_statements(path: Path) -> list[str]:
    """Statements of a SQL file (they must not contain ";" inside literals)."""
    return [
        statement.strip() for statement in path.read_text("utf-8").split(";") if statement.strip()
    ]


@pytest.fixture(scope="session")
def pg_engine() -> Engine:
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        message = "TEST_DATABASE_URL no está definida: pruebas con PostgreSQL omitidas"
        if os.environ.get("REQUIRE_TEST_DATABASE") == "1":  # CI must not skip them silently
            pytest.fail(message, pytrace=False)
        pytest.skip(message)
    try:
        ensure_safe_test_database(url)
    except UnsafeTestDatabaseError as error:
        pytest.fail(str(error), pytrace=False)
    engine = make_engine(url)
    with engine.begin() as connection:
        connection.execute(text(f"DROP TABLE IF EXISTS {', '.join(TABLES)} CASCADE"))
        for statement in sql_statements(SCHEMA):
            connection.exec_driver_sql(statement)
    yield engine
    engine.dispose()


@pytest.fixture
def pg_clean(pg_engine: Engine) -> Engine:
    """The test database with empty tables and identities restarted."""
    with pg_engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
    return pg_engine


def insert_reference_rows(session: Session) -> None:
    """Same catalog as the unit tests, with the same ids.

    user 1 (``tests.fakes.users``); location 1 Casa; cameras 1 Sala, 2 Patio;
    zone 1 Escalera (camera 1);
    subject 1 Rosa; event types 1 Caída (4), 2 Merodeo (2), 3 Ruido (1), 4 Humo (3).
    """
    session.add(UserRow(name=TEST_NAME, email=TEST_EMAIL, password_hash=TEST_PASSWORD_HASH))
    session.flush()
    session.add(LocationRow(name="Casa", description=None, user_id=1))
    session.flush()
    session.add_all(
        [
            CameraRow(name="Sala", ip_address="192.0.2.1", status="active", location_id=1),
            CameraRow(name="Patio", ip_address="192.0.2.2", status="active", location_id=1),
        ]
    )
    session.flush()
    session.add(ZoneRow(name="Escalera", coordinates=SQUARE, is_active=True, camera_id=1))
    session.add(SubjectRow(name="Rosa", subject_type="elderly", description=None, user_id=1))
    for name, severity in [("Caída", 4), ("Merodeo", 2), ("Ruido", 1), ("Humo", 3)]:
        session.add(EventTypeRow(name=name, severity_level=severity))
        session.flush()
    session.commit()


@pytest.fixture
def pg_seeded(pg_clean: Engine) -> Engine:
    """The test database with the reference catalog and no events."""
    with Session(pg_clean) as session:
        insert_reference_rows(session)
    return pg_clean
