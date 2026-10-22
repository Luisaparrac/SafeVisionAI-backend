"""Unit of work port: groups repository changes into one transaction."""

from types import TracebackType
from typing import Protocol, Self, runtime_checkable

from safevision.application.ports.repositories import (
    AlertRepository,
    CameraRepository,
    CatalogRepository,
    EventRepository,
    EventTypeRepository,
    UserRepository,
)


@runtime_checkable
class UnitOfWork(Protocol):
    """Used as a context manager; leaving it without ``commit`` discards the changes.

    ::

        with uow:
            uow.events.update(event)
            uow.commit()
    """

    events: EventRepository
    alerts: AlertRepository
    event_types: EventTypeRepository
    cameras: CameraRepository
    catalog: CatalogRepository
    users: UserRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Rolls back whatever was not committed."""
        ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...
