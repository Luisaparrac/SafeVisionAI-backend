import pytest

from safevision.application.ports.repositories import CatalogRepository
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from tests.fakes.repositories import InMemoryCatalogRepository


@pytest.fixture
def repo() -> InMemoryCatalogRepository:
    repo = InMemoryCatalogRepository()
    repo.locations.add(Location(name="Casa", user_id=1))
    repo.locations.add(Location(name="Oficina", user_id=1))
    repo.subjects.add(Subject(name="Rosa", subject_type="elderly", user_id=1))
    return repo


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, CatalogRepository)


def test_locations(repo):
    assert repo.get_location(2).name == "Oficina"
    assert repo.get_location(3) is None
    assert [loc.name for loc in repo.list_locations()] == ["Casa", "Oficina"]


def test_subjects(repo):
    assert repo.get_subject(1).name == "Rosa"
    assert repo.get_subject(2) is None
    assert len(repo.list_subjects()) == 1


def test_snapshot_and_restore(repo):
    state = repo.snapshot()
    repo.subjects.add(Subject(name="Toby", subject_type="pet", user_id=1))
    repo.restore(state)
    assert len(repo.list_subjects()) == 1
