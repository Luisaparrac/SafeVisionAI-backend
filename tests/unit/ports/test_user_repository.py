import pytest

from safevision.application.ports.repositories import UserRepository
from safevision.domain.model.user import User
from tests.fakes.repositories import InMemoryUserRepository


@pytest.fixture
def repo() -> InMemoryUserRepository:
    repo = InMemoryUserRepository()
    repo.add(User(name="Ana", email="Ana@Example.com", password_hash="x"))
    repo.add(User(name="Luis", email="luis@example.com", password_hash="y"))
    repo.add(User(name="Otra Ana", email="ana@example.com", password_hash="z"))
    return repo


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, UserRepository)


def test_get(repo):
    assert repo.get(2).name == "Luis"
    assert repo.get(9) is None


def test_find_by_email_ignores_case_and_spaces(repo):
    assert [u.name for u in repo.find_by_email(" LUIS@example.com ")] == ["Luis"]


def test_add_assigns_an_id(repo):
    created = repo.add(User(name="Eva", email="eva@example.com", password_hash="w"))
    assert (created.id, repo.get(created.id).email) == (4, "eva@example.com")


def test_replace_password_hash_needs_the_current_one(repo):
    assert repo.replace_password_hash(2, "otro", "nuevo") is False
    assert repo.get(2).password_hash == "y"
    assert repo.replace_password_hash(2, "y", "nuevo") is True
    assert repo.get(2).password_hash == "nuevo"
    assert repo.replace_password_hash(99, "y", "nuevo") is False


def test_find_by_email_returns_every_match_by_id(repo):
    assert [u.id for u in repo.find_by_email("ana@example.com")] == [1, 3]
    assert repo.find_by_email("nadie@example.com") == []
