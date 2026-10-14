from datetime import UTC, datetime, timedelta

import pytest

from safevision.application.ports.repositories import AlertRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.values import AlertStatus
from tests.fakes.repositories import InMemoryAlertRepository

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


def new_alert(event_id: int = 1, **overrides) -> Alert:
    return Alert(**({"event_id": event_id, "level": 2, "created_at": T0} | overrides))


@pytest.fixture
def repo() -> InMemoryAlertRepository:
    return InMemoryAlertRepository()


def test_fake_satisfies_the_port(repo):
    assert isinstance(repo, AlertRepository)


def test_add_get_update(repo):
    alert = repo.add(new_alert())
    assert alert.id == 1
    alert.close(T0 + timedelta(minutes=1))
    assert repo.get(1).status is AlertStatus.ACTIVE
    repo.update(alert)
    assert repo.get(1).status is AlertStatus.RESOLVED


def test_update_of_missing_alert_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(new_alert(id=3))


def test_find_by_event_oldest_first(repo):
    repo.add(new_alert(event_id=1))
    repo.add(new_alert(event_id=2))
    repo.add(new_alert(event_id=1))
    assert [a.id for a in repo.find_by_event(1)] == [1, 3]
    assert repo.find_by_event(9) == []
