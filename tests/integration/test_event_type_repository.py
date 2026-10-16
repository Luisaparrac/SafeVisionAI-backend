import pytest

from safevision.adapters.outbound.persistence.repositories import SqlAlchemyEventTypeRepository
from safevision.application.ports.repositories import EventTypeRepository
from safevision.domain.model.values import Severity

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session):
    return SqlAlchemyEventTypeRepository(session)


def test_satisfies_the_port(repo):
    assert isinstance(repo, EventTypeRepository)


def test_get(repo):
    caida = repo.get(1)
    assert (caida.id, caida.name, caida.severity) == (1, "Caída", Severity(4))
    assert repo.get(99) is None


def test_find_by_name_ignores_case_and_spaces(repo):
    assert repo.find_by_name("caída").id == 1
    assert repo.find_by_name("  MERODEO ").id == 2
    assert repo.find_by_name("Incendio") is None


def test_list_all_most_severe_first_then_by_name(repo):
    assert [t.name for t in repo.list_all()] == ["Caída", "Humo", "Merodeo", "Ruido"]
