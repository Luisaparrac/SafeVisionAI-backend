from tests.fakes.repositories import (
    InMemoryAlertRepository,
    InMemoryCameraRepository,
    InMemoryCatalogRepository,
    InMemoryEventRepository,
    InMemoryEventTypeRepository,
    InMemoryUserRepository,
)


class FakeUnitOfWork:
    """In-memory unit of work whose rollback really undoes uncommitted changes.

    The repositories outlive each ``with`` block, like a database does.
    """

    def __init__(self) -> None:
        self.events = InMemoryEventRepository()
        self.alerts = InMemoryAlertRepository()
        self.event_types = InMemoryEventTypeRepository()
        self.cameras = InMemoryCameraRepository()
        self.catalog = InMemoryCatalogRepository()
        self.users = InMemoryUserRepository()
        self.commits = 0
        self._committed_state = self._snapshot()

    def __enter__(self) -> "FakeUnitOfWork":
        self._committed_state = self._snapshot()
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.rollback()

    def commit(self) -> None:
        self._committed_state = self._snapshot()
        self.commits += 1

    def rollback(self) -> None:
        for repo, state in zip(self._repositories(), self._committed_state, strict=True):
            repo.restore(state)

    def _repositories(self) -> tuple:
        return (
            self.events,
            self.alerts,
            self.event_types,
            self.cameras,
            self.catalog,
            self.users,
        )

    def _snapshot(self) -> tuple:
        return tuple(repo.snapshot() for repo in self._repositories())
