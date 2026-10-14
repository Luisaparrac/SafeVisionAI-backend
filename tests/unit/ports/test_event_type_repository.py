import pytest

from safevision.application.ports.repositories import EventTypeRepository
from safevision.domain.model.event_type import EventType
from tests.fakes.repositories import InMemoryEventTypeRepository


@pytest.fixture
def repo() -> InMemoryEventTypeRepository:
    repo = InMemoryEventTypeRepository()
    for name, severity in [("Merodeo", 2), ("Caída", 4), ("Abandono", 4), ("Ruido", 1)]:
        repo.add(EventType(name=name, severity=severity))
    return repo


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, EventTypeRepository)


def test_get(repo):
    assert repo.get(2).name == "Caída"
    assert repo.get(42) is None


def test_find_by_name_ignores_case(repo):
    assert repo.find_by_name("caída").id == 2
    assert repo.find_by_name("  MERODEO ").id == 1
    assert repo.find_by_name("Incendio") is None


def test_list_all_most_severe_first_then_by_name(repo):
    assert [t.name for t in repo.list_all()] == ["Abandono", "Caída", "Merodeo", "Ruido"]
