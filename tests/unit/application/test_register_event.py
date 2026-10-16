from datetime import timedelta

import pytest

from safevision.application.services.alert_board import AlertBoard
from safevision.application.services.event_deduplicator import EventDeduplicator
from safevision.application.use_cases.register_event import RegisterEvent, RegisterEventCommand
from safevision.domain.errors import NotFoundError, ValidationError
from safevision.domain.model.values import AlertStatus, EventStatus, Severity


@pytest.fixture
def board() -> AlertBoard:
    return AlertBoard(history_capacity=10)


@pytest.fixture
def register(uow, clock, board, presenter) -> RegisterEvent:
    deduplicator = EventDeduplicator(timedelta(seconds=30), clock.now)
    return RegisterEvent(uow, clock, board, deduplicator, presenter)


def test_creates_event_and_alert_with_type_severity(register, uow, clock, board):
    result = register.execute(
        RegisterEventCommand(
            camera_id=1, event_type="caída", subject_id=1, zone_id=1, confidence=0.9
        )
    )
    assert result.created
    assert (result.view.id, result.view.type, result.view.priority) == (1, "Caída", "Alto")
    event = uow.events.get(1)
    assert event.status is EventStatus.PENDING
    assert event.occurred_at == clock.now()
    assert (event.subject_id, event.zone_id, event.confidence.value) == (1, 1, 0.9)
    [alert] = uow.alerts.find_by_event(1)
    assert (alert.level, alert.status, alert.created_at) == (
        Severity(4),
        AlertStatus.ACTIVE,
        event.occurred_at,
    )
    assert uow.commits == 1
    assert [e.event_id for e in board.pending(5)] == [1]
    assert board.recent(5) == [result.view]


def test_event_type_by_id_takes_precedence(register):
    result = register.execute(
        RegisterEventCommand(camera_id=1, event_type_id=2, event_type="Caída")
    )
    assert result.view.type == "Merodeo"


@pytest.mark.parametrize(
    ("command", "message"),
    [
        (RegisterEventCommand(camera_id=9, event_type_id=1), "Cámara 9"),
        (RegisterEventCommand(camera_id=1, event_type_id=1, subject_id=9), "Sujeto 9"),
        (RegisterEventCommand(camera_id=1, event_type_id=1, zone_id=9), "Zona 9"),
        (RegisterEventCommand(camera_id=2, event_type_id=1, zone_id=1), "Zona 1 de la cámara 2"),
        (RegisterEventCommand(camera_id=1, event_type_id=9), "Tipo de evento 9"),
        (RegisterEventCommand(camera_id=1, event_type="Incendio"), "Tipo de evento"),
    ],
)
def test_missing_references(register, uow, board, command, message):
    with pytest.raises(NotFoundError, match=message):
        register.execute(command)
    assert uow.events.get(1) is None
    assert board.pending_count() == 0


@pytest.mark.parametrize("name", [None, ""])
def test_event_type_is_required(register, name):
    with pytest.raises(ValidationError, match="event_type"):
        register.execute(RegisterEventCommand(camera_id=1, event_type=name))


@pytest.mark.parametrize("overrides", [{"confidence": 1.5}, {"detected_class": "bird"}])
def test_invalid_detection_values_store_nothing(register, uow, overrides):
    with pytest.raises(ValidationError):
        register.execute(RegisterEventCommand(camera_id=1, event_type_id=1, **overrides))
    assert uow.events.get(1) is None
    assert uow.alerts.find_by_event(1) == []


def test_repeated_detection_returns_the_first_event(register, uow, clock, board):
    first = register.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    clock.advance(10)
    again = register.execute(RegisterEventCommand(camera_id=1, event_type_id=1, confidence=0.5))
    assert not again.created
    assert again.view == first.view
    assert uow.events.get(2) is None
    assert board.pending_count() == 1


def test_different_subject_or_window_elapsed_creates_new_event(register, clock):
    register.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    assert register.execute(
        RegisterEventCommand(camera_id=1, event_type_id=1, subject_id=1)
    ).created
    clock.advance(30)
    assert register.execute(RegisterEventCommand(camera_id=1, event_type_id=1)).created


def test_failed_commit_leaves_memory_untouched(register, uow, board, monkeypatch):
    def failing_commit():
        raise RuntimeError("database down")

    monkeypatch.setattr(uow, "commit", failing_commit)
    with pytest.raises(RuntimeError):
        register.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    assert uow.events.get(1) is None
    assert board.pending_count() == 0
    monkeypatch.undo()
    # The failed attempt was not remembered, so the retry is registered.
    assert register.execute(RegisterEventCommand(camera_id=1, event_type_id=1)).created


def test_new_alert_is_published_after_the_commit(uow, clock, board, presenter):
    from safevision.application.dto import NEW_ALERT
    from tests.fakes.notifier import RecordingNotifier

    notifier = RecordingNotifier()
    deduplicator = EventDeduplicator(timedelta(seconds=30), clock.now)
    register = RegisterEvent(uow, clock, board, deduplicator, presenter, notifier)
    result = register.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    [notification] = notifier.published
    assert notification.kind == NEW_ALERT
    assert notification.event == result.view
    assert (notification.alert.alert_id, notification.alert.level) == (1, "Alto")
    assert notification.alert.status == "Activa"
    assert uow.commits == 1

    # A repeated detection raises no new alert, so nothing is published.
    register.execute(RegisterEventCommand(camera_id=1, event_type_id=1))
    assert len(notifier.published) == 1


def test_failed_registration_publishes_nothing(uow, clock, board, presenter):
    from tests.fakes.notifier import RecordingNotifier

    notifier = RecordingNotifier()
    deduplicator = EventDeduplicator(timedelta(seconds=30), clock.now)
    register = RegisterEvent(uow, clock, board, deduplicator, presenter, notifier)
    with pytest.raises(NotFoundError):
        register.execute(RegisterEventCommand(camera_id=99, event_type_id=1))
    assert notifier.published == []
