import pytest

from safevision.application.use_cases.mark_alert_seen import MarkAlertSeen
from safevision.domain.errors import InvalidTransitionError, NotFoundError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import AlertStatus


@pytest.fixture
def mark_seen(uow, presenter) -> MarkAlertSeen:
    return MarkAlertSeen(uow, presenter)


def stored_alert(uow, clock, **overrides) -> Alert:
    event = uow.events.add(Event(camera_id=1, event_type_id=2, occurred_at=clock.now()))
    data = {"event_id": event.id, "level": 2, "created_at": event.occurred_at}
    alert = uow.alerts.add(Alert(**(data | overrides)))
    uow.commit()
    return alert


def test_active_alert_becomes_seen(mark_seen, uow, clock):
    alert = stored_alert(uow, clock)
    view = mark_seen.execute(alert.id)
    assert (view.alert_id, view.level, view.status) == (alert.id, "Medio", "Vista")
    assert view.event.id == alert.event_id
    assert view.event.status == "Pendiente"
    assert uow.alerts.get(alert.id).status is AlertStatus.SEEN


def test_repeating_is_a_no_op(mark_seen, uow, clock):
    alert = stored_alert(uow, clock, status="seen")
    assert mark_seen.execute(alert.id).status == "Vista"
    assert uow.commits == 1


@pytest.mark.parametrize("status", ["resolved", "dismissed"])
def test_closed_alert_is_rejected(mark_seen, uow, clock, status):
    alert = stored_alert(uow, clock, status=status, attended_at=clock.now())
    with pytest.raises(InvalidTransitionError):
        mark_seen.execute(alert.id)


def test_unknown_alert(mark_seen):
    with pytest.raises(NotFoundError, match="Alerta 3"):
        mark_seen.execute(3)
