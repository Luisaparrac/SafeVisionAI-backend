"""The ORM mapping matches the reference schema, without touching any database."""

import re
from pathlib import Path

import pytest

from safevision.adapters.outbound.persistence import orm

SCHEMA = Path(__file__).resolve().parents[2] / "integration" / "schema.sql"

_TABLE = re.compile(r"CREATE TABLE (\w+) \((.*?)\n\);", re.DOTALL)
_COLUMN = re.compile(r"^\s{2}(\w+) (\w+)")


def schema_columns() -> dict[str, set[str]]:
    """Column names per table, read from schema.sql (constraint lines are skipped)."""
    tables: dict[str, set[str]] = {}
    for name, body in _TABLE.findall(SCHEMA.read_text(encoding="utf-8")):
        columns = set()
        for line in body.splitlines():
            match = _COLUMN.match(line)
            if match and match.group(1) != "CONSTRAINT":
                columns.add(match.group(1))
        tables[name] = columns
    return tables


MAPPED = {mapper.class_.__tablename__: mapper.class_ for mapper in orm.Base.registry.mappers}


def test_schema_parser_reads_every_table():
    assert len(schema_columns()) == 8


@pytest.mark.parametrize("table", sorted(MAPPED))
def test_mapped_columns_match_the_schema(table):
    mapped = {column.name for column in MAPPED[table].__table__.columns}
    assert mapped == schema_columns()[table]


@pytest.mark.parametrize("table", sorted(MAPPED))
def test_primary_key_is_the_identity_column(table):
    keys = [column.name for column in MAPPED[table].__table__.primary_key]
    assert keys == [f"{table.removesuffix('s')}_id"]


def test_catalog_tables_are_mapped():
    assert {"users", "locations", "subjects", "event_types"} <= set(MAPPED)
