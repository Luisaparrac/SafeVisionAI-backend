"""Session handling of the SQLAlchemy unit of work, with a recording fake session."""

import threading

import pytest
from sqlalchemy.exc import OperationalError

from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.application.errors import StorageUnavailableError
from safevision.application.ports.unit_of_work import UnitOfWork


class RecordingSession:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def commit(self) -> None:
        self.calls.append("commit")

    def rollback(self) -> None:
        self.calls.append("rollback")

    def close(self) -> None:
        self.calls.append("close")


class RecordingFactory:
    def __init__(self) -> None:
        self.sessions: list[RecordingSession] = []

    def __call__(self) -> RecordingSession:
        session = RecordingSession()
        self.sessions.append(session)
        return session


@pytest.fixture
def factory():
    return RecordingFactory()


def test_satisfies_the_port(factory):
    assert isinstance(SqlAlchemyUnitOfWork(factory), UnitOfWork)


def test_commit_then_leaving_closes_the_session(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with uow:
        uow.commit()
    assert factory.sessions[0].calls == ["commit", "rollback", "close"]


def test_an_exception_discards_the_changes(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with pytest.raises(ValueError), uow:
        raise ValueError
    assert factory.sessions[0].calls == ["rollback", "close"]


def test_each_block_opens_a_new_session(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with uow:
        first = uow.events
    with uow:
        second = uow.events
    assert len(factory.sessions) == 2
    assert first is not second


def test_repositories_share_the_session_of_the_block(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with uow:
        sessions = {
            repo._session
            for repo in (uow.events, uow.alerts, uow.event_types, uow.cameras, uow.catalog)
        }
    assert sessions == {factory.sessions[0]}


def test_repositories_are_unavailable_outside_the_block(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with pytest.raises(RuntimeError, match="outside"):
        uow.events  # noqa: B018
    with pytest.raises(RuntimeError, match="outside"):
        uow.commit()


def test_nested_use_in_the_same_thread_is_rejected(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    with uow, pytest.raises(RuntimeError, match="already"), uow:
        pass


def test_threads_get_independent_sessions(factory):
    uow = SqlAlchemyUnitOfWork(factory)
    inside = threading.Barrier(2)
    seen: dict[str, object] = {}

    def work(name: str) -> None:
        with uow:
            inside.wait(timeout=5)  # both threads are inside their block at once
            seen[name] = uow.events._session

    threads = [threading.Thread(target=work, args=(name,)) for name in ("a", "b")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert seen["a"] is not seen["b"]
    assert all(s.calls == ["rollback", "close"] for s in factory.sessions)


def connection_lost() -> OperationalError:
    return OperationalError("SELECT 1", {}, Exception("host=db.example.com password=x"))


def test_database_errors_leave_the_block_as_application_errors(factory, caplog):
    uow = SqlAlchemyUnitOfWork(factory)
    with pytest.raises(StorageUnavailableError) as info, uow:
        raise connection_lost()
    assert info.value.__cause__ is None
    assert info.value.__suppress_context__
    assert "db.example.com" not in caplog.text
    assert factory.sessions[0].calls == ["rollback", "close"]


def test_a_failing_rollback_still_closes_the_session(factory):
    uow = SqlAlchemyUnitOfWork(factory)

    def broken_rollback() -> None:
        raise connection_lost()

    with pytest.raises(StorageUnavailableError), uow:
        session = factory.sessions[0]
        session.rollback = broken_rollback
        raise connection_lost()
    assert session.calls == ["close"]
