from datetime import UTC, datetime

import pytest

from safevision.domain.errors import InvalidTransitionError, ValidationError
from safevision.domain.model.camera import Camera
from safevision.domain.model.event import Event
from safevision.domain.model.event_type import EventType
from safevision.domain.model.values import Confidence, DetectedClass, EventStatus
from safevision.domain.model.zone import Zone

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)
SQUARE = [[0, 0], [1, 0], [1, 1]]
CAMERA = Camera(id=1, name="Sala", ip_address="192.0.2.1", location_id=1)
FALL = EventType(id=7, name="Caída", severity=4)


def make_event(**overrides) -> Event:
    return Event(**({"camera_id": 1, "event_type_id": 7, "occurred_at": NOW} | overrides))


def test_defaults():
    event = make_event()
    assert event.status is EventStatus.PENDING
    assert event.detected_class is DetectedClass.PERSON
    assert event.is_open


def test_raw_values_are_converted():
    event = make_event(status="in_review", detected_class="dog", confidence=0.9)
    assert event.status is EventStatus.IN_REVIEW
    assert event.detected_class is DetectedClass.DOG
    assert event.confidence == Confidence(0.9)


@pytest.mark.parametrize(
    "overrides",
    [
        {"occurred_at": datetime(2026, 1, 1)},
        {"confidence": 1.5},
        {"detected_class": "bird"},
        {"status": "closed"},
        {"camera_id": None},
        {"zone_id": 0},
    ],
)
def test_invalid_event(overrides):
    with pytest.raises(ValidationError):
        make_event(**overrides)


def test_register_with_zone_of_the_camera():
    zone = Zone(id=5, name="Escalera", camera_id=1, polygon=SQUARE)
    event = Event.register(
        camera=CAMERA, event_type=FALL, occurred_at=NOW, zone=zone, confidence=0.8
    )
    assert (event.camera_id, event.event_type_id, event.zone_id) == (1, 7, 5)
    assert event.status is EventStatus.PENDING
    assert event.id is None


def test_register_rejects_zone_of_another_camera():
    zone = Zone(id=5, name="Patio", camera_id=2, polygon=SQUARE)
    with pytest.raises(ValidationError, match="no pertenece"):
        Event.register(camera=CAMERA, event_type=FALL, occurred_at=NOW, zone=zone)


def test_register_requires_persisted_references():
    new_camera = Camera(name="Nueva", ip_address="192.0.2.2", location_id=1)
    with pytest.raises(ValidationError):
        Event.register(camera=new_camera, event_type=FALL, occurred_at=NOW)


def test_event_in_review_can_be_resolved():
    # in_review is set by other clients of the shared database.
    event = make_event(status="in_review")
    assert event.is_open
    event.resolve()
    assert event.status is EventStatus.RESOLVED
    assert not event.is_open


def test_mark_false_alarm_directly():
    event = make_event()
    event.mark_false_alarm()
    assert event.status is EventStatus.FALSE_ALARM


@pytest.mark.parametrize("action", ["resolve", "mark_false_alarm"])
def test_closed_event_cannot_change(action):
    event = make_event(status="resolved")
    with pytest.raises(InvalidTransitionError):
        getattr(event, action)()
    assert event.status is EventStatus.RESOLVED
