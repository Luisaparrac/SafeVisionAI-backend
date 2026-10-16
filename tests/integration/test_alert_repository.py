from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from safevision.adapters.outbound.persistence.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyEventRepository,
)
from safevision.application.ports.repositories import AlertRepository
from safevision.domain.errors import NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import AlertStatus, Severity

pytestmark = pytest.mark.integration

T0 = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)


@pytest.fixture
def repo(session):
    events = SqlAlchemyEventRepository(session)
    for _ in range(2):
        events.add(Event(camera_id=1, event_type_id=1, occurred_at=T0))
    return SqlAlchemyAlertRepository(session)


def new_alert(event_id: int = 1, **overrides) -> Alert:
    return Alert(**({"event_id": event_id, "level": 4, "created_at": T0} | overrides))


def test_satisfies_the_port(repo):
    assert isinstance(repo, AlertRepository)


def test_add_and_get(repo):
    alert = repo.add(new_alert())
    assert alert.id == 1
    loaded = repo.get(1)
    assert loaded == alert
    assert (loaded.level, loaded.status, loaded.created_at) == (
        Severity(4),
        AlertStatus.ACTIVE,
        T0,
    )
    assert repo.get(99) is None


def test_update_closes_the_alert(repo):
    alert = repo.add(new_alert())
    alert.close(T0 + timedelta(minutes=3), by_user_id=1)
    repo.update(alert)
    loaded = repo.get(alert.id)
    assert loaded.status is AlertStatus.RESOLVED
    assert loaded.attended_at == T0 + timedelta(minutes=3)
    assert loaded.attended_by_user_id == 1


def test_update_of_missing_alert_fails(repo):
    with pytest.raises(NotFoundError):
        repo.update(new_alert(id=7))


def test_find_by_event_oldest_first(repo):
    repo.add(new_alert(event_id=1))
    repo.add(new_alert(event_id=2))
    repo.add(new_alert(event_id=1, level=2))
    assert [a.id for a in repo.find_by_event(1)] == [1, 3]
    assert repo.find_by_event(99) == []


def test_alert_of_missing_event_is_rejected_by_the_database(repo):
    with pytest.raises(IntegrityError):
        repo.add(new_alert(event_id=99))
