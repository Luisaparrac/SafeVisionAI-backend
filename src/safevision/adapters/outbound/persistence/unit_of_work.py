"""SQLAlchemy implementation of the UnitOfWork port.

One instance is shared by every use case, while the HTTP server runs requests
in several threads. Each thread therefore gets its own session and
repositories, kept in thread-local storage for the length of the ``with``.
"""

import threading
from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session, sessionmaker

from safevision.adapters.outbound.persistence.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyCameraRepository,
    SqlAlchemyCatalogRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyEventTypeRepository,
)


class _Transaction:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.events = SqlAlchemyEventRepository(session)
        self.alerts = SqlAlchemyAlertRepository(session)
        self.event_types = SqlAlchemyEventTypeRepository(session)
        self.cameras = SqlAlchemyCameraRepository(session)
        self.catalog = SqlAlchemyCatalogRepository(session)


class SqlAlchemyUnitOfWork:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._local = threading.local()

    def __enter__(self) -> Self:
        if getattr(self._local, "transaction", None) is not None:
            raise RuntimeError("the unit of work is already in use in this thread")
        self._local.transaction = _Transaction(self._session_factory())
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        transaction = self._current()
        self._local.transaction = None
        try:
            transaction.session.rollback()
        finally:
            transaction.session.close()

    def commit(self) -> None:
        self._current().session.commit()

    def rollback(self) -> None:
        self._current().session.rollback()

    @property
    def events(self) -> SqlAlchemyEventRepository:
        return self._current().events

    @property
    def alerts(self) -> SqlAlchemyAlertRepository:
        return self._current().alerts

    @property
    def event_types(self) -> SqlAlchemyEventTypeRepository:
        return self._current().event_types

    @property
    def cameras(self) -> SqlAlchemyCameraRepository:
        return self._current().cameras

    @property
    def catalog(self) -> SqlAlchemyCatalogRepository:
        return self._current().catalog

    def _current(self) -> _Transaction:
        transaction = getattr(self._local, "transaction", None)
        if transaction is None:
            raise RuntimeError("the unit of work is used outside a 'with' block")
        return transaction
