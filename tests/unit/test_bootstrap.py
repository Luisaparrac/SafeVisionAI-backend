"""The composition root wires every use case around shared adapters."""

from safevision.adapters.inbound.http.container import Container
from safevision.adapters.outbound.persistence.unit_of_work import SqlAlchemyUnitOfWork
from safevision.adapters.outbound.system_clock import SystemClock
from safevision.application.use_cases.register_event import RegisterEventCommand
from safevision.bootstrap import build_container, build_production_container
from safevision.config.settings import Settings
from tests.fakes.catalog import seed_reference_catalog
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork

SETTINGS = Settings(
    database_url="postgresql://test:test@localhost/test",
    iot_api_key="test-key",
    session_secret="test-session-secret-0123456789abcdef",
    frontend_origins=("http://localhost:5173",),
    history_capacity=3,
)


def build(clock: FakeClock | None = None) -> Container:
    uow = FakeUnitOfWork()
    seed_reference_catalog(uow)
    return build_container(SETTINGS, uow, clock or FakeClock())


def test_settings_reach_the_http_adapter():
    container = build()
    assert container.iot_api_key == "test-key"
    assert container.cors_origins == ("http://localhost:5173",)
    assert "test-key" not in repr(container)


def test_use_cases_share_the_board():
    container = build()
    view = container.register_event.execute(RegisterEventCommand(camera_id=1, event_type_id=1)).view
    assert container.get_recent_events.execute(10) == [view]
    assert [a.event for a in container.get_pending_alerts.execute(10)] == [view]
    assert container.get_metrics.execute().pending == 1
    container.review_event.execute(view.id)
    assert container.get_metrics.execute().pending == 0


def test_history_capacity_comes_from_the_settings():
    container = build()
    for camera_id, event_type_id in [(1, 1), (1, 2), (1, 3), (1, 4)]:
        container.register_event.execute(
            RegisterEventCommand(camera_id=camera_id, event_type_id=event_type_id)
        )
    assert len(container.get_recent_events.execute(10)) == 3


def test_deduplication_window_comes_from_the_settings():
    clock = FakeClock()
    container = build(clock)
    command = RegisterEventCommand(camera_id=2, event_type_id=3)
    first = container.register_event.execute(command)
    clock.advance(SETTINGS.dedup_window_seconds - 1)
    assert container.register_event.execute(command).created is False
    clock.advance(1)
    assert container.register_event.execute(command).view.id != first.view.id


def test_production_container_uses_postgres_and_the_system_clock_without_connecting():
    container = build_production_container(SETTINGS)
    register = container.register_event
    assert isinstance(register._uow, SqlAlchemyUnitOfWork)
    assert isinstance(register._clock, SystemClock)


def test_window_counts_from_the_first_detection():
    # A situation that lasts produces one alert per window, not one per detection.
    clock = FakeClock()
    container = build(clock)
    command = RegisterEventCommand(camera_id=1, event_type_id=2)
    first = container.register_event.execute(command).view.id
    for _ in range(5):
        clock.advance(SETTINGS.dedup_window_seconds / 5 - 1)
        assert container.register_event.execute(command).view.id == first
    clock.advance(5)
    assert container.register_event.execute(command).created is True
