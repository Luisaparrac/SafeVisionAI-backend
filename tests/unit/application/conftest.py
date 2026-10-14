"""Fixtures for use case tests: a seeded in-memory database and a fake clock."""

from zoneinfo import ZoneInfo

import pytest

from safevision.application.presenter import EventPresenter
from safevision.domain.model.camera import Camera
from safevision.domain.model.event_type import EventType
from safevision.domain.model.location import Location
from safevision.domain.model.subject import Subject
from safevision.domain.model.zone import Zone
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork

TIMEZONE = ZoneInfo("America/Bogota")
SQUARE = [[0, 0], [1, 0], [1, 1], [0, 1]]


def seed(uow: FakeUnitOfWork) -> None:
    """Ids: location 1 Casa; cameras 1 Sala, 2 Patio; zone 1 Escalera (camera 1);
    subject 1 Rosa; event types 1 Caída (4), 2 Merodeo (2), 3 Ruido (1), 4 Humo (3)."""
    uow.catalog.locations.add(Location(name="Casa", user_id=1))
    uow.cameras.add(Camera(name="Sala", ip_address="192.0.2.1", location_id=1))
    uow.cameras.add(Camera(name="Patio", ip_address="192.0.2.2", location_id=1))
    uow.cameras.zones.add(Zone(name="Escalera", camera_id=1, polygon=SQUARE))
    uow.catalog.subjects.add(Subject(name="Rosa", subject_type="elderly", user_id=1))
    for name, severity in [("Caída", 4), ("Merodeo", 2), ("Ruido", 1), ("Humo", 3)]:
        uow.event_types.add(EventType(name=name, severity=severity))
    uow.commit()
    uow.commits = 0


@pytest.fixture
def uow() -> FakeUnitOfWork:
    uow = FakeUnitOfWork()
    seed(uow)
    return uow


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def presenter() -> EventPresenter:
    return EventPresenter(TIMEZONE)
