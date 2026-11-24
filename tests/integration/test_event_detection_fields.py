"""Detected class, confidence and evidence round trip through PostgreSQL."""

import pytest
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.database import make_session_factory
from safevision.adapters.outbound.persistence.orm import EventRow
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from tests.contract.conftest import KEY, hexagonal_client

pytestmark = pytest.mark.integration

EVIDENCE = "https://example.com/evidencias/0001.jpg"


@pytest.fixture
def client(pg_seeded):
    with hexagonal_client(SqlAlchemyUnitOfWork(make_session_factory(pg_seeded))) as client:
        yield client


def register(client, **body) -> dict:
    response = client.post(
        "/api/eventos", json={"camera_id": 1, "event_type_id": 1} | body, headers=KEY
    )
    assert response.status_code == 201, response.text
    return response.json()


def detection(event: dict) -> tuple:
    keys = ("detected_class", "detected_class_label", "confidence", "evidence_url")
    return tuple(event[key] for key in keys)


def test_the_values_sent_by_the_iot_module_come_back(client, pg_seeded):
    created = register(client, detected_class="dog", confidence=0.87, evidence_url=EVIDENCE)

    read = client.get(f"/api/eventos/{created['id']}").json()

    assert detection(read) == detection(created) == ("dog", "Perro", 0.87, EVIDENCE)
    with Session(pg_seeded) as session:
        row = session.get(EventRow, created["id"])
        assert (row.detected_class, float(row.confidence), row.evidence_url) == (
            "dog",
            0.87,
            EVIDENCE,
        )


def test_an_event_without_them_shows_the_defaults(client):
    created = register(client, event_type_id=2)
    read = client.get(f"/api/eventos/{created['id']}").json()
    assert detection(read) == ("person", "Persona", None, None)


def test_a_stored_unsafe_link_is_kept_but_not_published(client, pg_seeded):
    created = register(client, evidence_url="javascript:alert(1)")
    assert client.get(f"/api/eventos/{created['id']}").json()["evidence_url"] is None
    with Session(pg_seeded) as session:
        assert session.get(EventRow, created["id"]).evidence_url == "javascript:alert(1)"
