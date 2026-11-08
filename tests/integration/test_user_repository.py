import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from safevision.adapters.outbound.persistence.orm import UserRow
from safevision.adapters.outbound.persistence.repositories import SqlAlchemyUserRepository
from safevision.application.ports.repositories import UserRepository
from safevision.domain.model.user import User

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(session):
    # User 1 ("usuario@example.com") comes from the reference rows.
    session.add(UserRow(name="Ana", email="Ana@Example.com", password_hash="hash-ana"))
    session.add(UserRow(name="Otra Ana", email="ana@example.com", password_hash="hash-otra"))
    session.flush()
    return SqlAlchemyUserRepository(session)


def test_satisfies_the_port(repo):
    assert isinstance(repo, UserRepository)


def test_get(repo):
    ana = repo.get(2)
    assert (ana.id, ana.name, ana.email, ana.password_hash) == (
        2,
        "Ana",
        "Ana@Example.com",
        "hash-ana",
    )
    assert repo.get(99) is None


def test_find_by_email_ignores_case_and_spaces(repo):
    assert [u.id for u in repo.find_by_email(" USUARIO@example.com ")] == [1]


def test_find_by_email_returns_every_match_by_id(repo):
    # The column is not unique in the shared schema.
    assert [u.name for u in repo.find_by_email("ana@example.com")] == ["Ana", "Otra Ana"]
    assert repo.find_by_email("nadie@example.com") == []


def test_add_uses_the_identity_of_the_table(repo):
    created = repo.add(User(name="Eva", email="eva@example.com", password_hash="hash-eva"))
    assert created.id == 4
    assert repo.get(4).password_hash == "hash-eva"


def test_the_table_rejects_an_invalid_email(repo):
    with pytest.raises(IntegrityError):
        repo.add(User(name="Eva", email="sin-arroba", password_hash="x"))


def test_lock_email_waits_for_the_transaction_that_holds_it(pg_seeded, session, repo):
    repo.lock_email(" Eva@Example.com ")
    with Session(pg_seeded) as other, other.begin():
        other.execute(text("SET LOCAL lock_timeout = '100ms'"))
        with pytest.raises(OperationalError):
            SqlAlchemyUserRepository(other).lock_email("eva@example.com")
    session.rollback()  # ends the transaction, which releases the lock
    with Session(pg_seeded) as other, other.begin():
        SqlAlchemyUserRepository(other).lock_email("eva@example.com")
