from datetime import UTC, datetime, timedelta

import pytest

from safevision.domain.errors import InvalidTransitionError, ValidationError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.values import AlertStatus, Severity

CREATED = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
LATER = CREATED + timedelta(minutes=5)


def make_alert(**overrides) -> Alert:
    return Alert(**({"event_id": 1, "level": 3, "created_at": CREATED} | overrides))


def test_new_alert_is_active():
    alert = make_alert()
    assert alert.status is AlertStatus.ACTIVE
    assert alert.level == Severity(3)
    assert alert.is_open
    assert alert.attended_at is None


def test_for_event_uses_the_event_type_severity():
    event = Event(id=9, camera_id=1, event_type_id=2, occurred_at=CREATED)
    alert = Alert.for_event(event, EventType(id=2, name="Caída", severity=4))
    assert (alert.event_id, alert.level, alert.created_at) == (9, Severity(4), CREATED)


def test_for_event_requires_persisted_event():
    event = Event(camera_id=1, event_type_id=2, occurred_at=CREATED)
    with pytest.raises(ValidationError):
        Alert.for_event(event, EventType(id=2, name="Caída", severity=4))


def test_seen_then_closed():
    alert = make_alert()
    alert.mark_seen()
    assert alert.status is AlertStatus.SEEN
    alert.close(LATER, by_user_id=3)
    assert alert.status is AlertStatus.RESOLVED
    assert (alert.attended_at, alert.attended_by_user_id) == (LATER, 3)
    assert not alert.is_open


def test_dismiss_at_creation_time_is_allowed():
    alert = make_alert()
    alert.dismiss(CREATED)
    assert alert.status is AlertStatus.DISMISSED
    assert alert.attended_at == CREATED


def test_close_before_creation_is_rejected_and_nothing_changes():
    alert = make_alert()
    with pytest.raises(ValidationError):
        alert.close(CREATED - timedelta(seconds=1))
    assert alert.status is AlertStatus.ACTIVE
    assert alert.attended_at is None


def test_close_needs_aware_time():
    with pytest.raises(ValidationError):
        make_alert().close(datetime(2026, 10, 14, 13, 0))


@pytest.mark.parametrize("action", ["close", "dismiss"])
def test_closed_alert_cannot_close_again(action):
    alert = make_alert()
    alert.close(LATER)
    with pytest.raises(InvalidTransitionError):
        getattr(alert, action)(LATER)
    with pytest.raises(InvalidTransitionError):
        alert.mark_seen()


def test_loaded_closed_alert_requires_attention_time():
    with pytest.raises(ValidationError):
        make_alert(status="resolved")
    assert make_alert(status="dismissed", attended_at=LATER).attended_at == LATER


def test_loaded_alert_with_attention_before_creation_is_rejected():
    with pytest.raises(ValidationError):
        make_alert(status="resolved", attended_at=CREATED - timedelta(hours=1))


@pytest.mark.parametrize("level", [0, 5])
def test_level_must_be_a_valid_severity(level):
    with pytest.raises(ValidationError):
        make_alert(level=level)
