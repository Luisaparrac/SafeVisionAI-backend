"""The test database reproduces the production structure, constraints included."""

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.orm import Base, CameraRow, EventTypeRow
from tests.integration.postgres import TABLES

pytestmark = pytest.mark.integration


def test_every_table_exists(pg_clean):
    assert set(inspect(pg_clean).get_table_names()) >= set(TABLES)
    assert set(Base.metadata.tables) == set(TABLES)


def test_reference_rows_get_predictable_ids(pg_seeded):
    with Session(pg_seeded) as session:
        names = session.execute(
            select(EventTypeRow.event_type_id, EventTypeRow.name).order_by(
                EventTypeRow.event_type_id
            )
        ).all()
        camera = session.get(CameraRow, 2)
    assert [tuple(row) for row in names] == [
        (1, "Caída"),
        (2, "Merodeo"),
        (3, "Ruido"),
        (4, "Humo"),
    ]
    assert camera.name == "Patio"


def test_check_constraints_are_enforced(pg_seeded):
    with pg_seeded.connect() as connection, pytest.raises(IntegrityError):
        connection.execute(text("UPDATE cameras SET status = 'broken' WHERE camera_id = 1"))
