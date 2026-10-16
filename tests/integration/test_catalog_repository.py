import pytest

from safevision.adapters.outbound.persistence.orm import LocationRow, SubjectRow
from safevision.adapters.outbound.persistence.repositories import SqlAlchemyCatalogRepository
from safevision.application.ports.repositories import CatalogRepository
from safevision.domain.model.values import SubjectType

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session):
    session.add(LocationRow(name="Oficina", description="Segundo piso", user_id=1))
    session.add(SubjectRow(name="Max", subject_type="pet", description=None, user_id=1))
    session.flush()
    return SqlAlchemyCatalogRepository(session)


def test_satisfies_the_port(repo):
    assert isinstance(repo, CatalogRepository)


def test_locations(repo):
    assert repo.get_location(2).description == "Segundo piso"
    assert repo.get_location(99) is None
    assert [loc.name for loc in repo.list_locations()] == ["Casa", "Oficina"]


def test_subjects(repo):
    rosa = repo.get_subject(1)
    assert (rosa.name, rosa.subject_type, rosa.user_id) == ("Rosa", SubjectType.ELDERLY, 1)
    assert repo.get_subject(99) is None
    assert [(s.id, s.name) for s in repo.list_subjects()] == [(1, "Rosa"), (2, "Max")]
