"""Fixtures for use case tests: a seeded in-memory database and a fake clock."""

from zoneinfo import ZoneInfo

import pytest

from safevision.application.presenter import EventPresenter
from tests.fakes.catalog import seed_reference_catalog
from tests.fakes.clock import FakeClock
from tests.fakes.unit_of_work import FakeUnitOfWork

TIMEZONE = ZoneInfo("America/Bogota")


@pytest.fixture
def uow() -> FakeUnitOfWork:
    """Reference catalog (see ``seed_reference_catalog``) and no events."""
    uow = FakeUnitOfWork()
    seed_reference_catalog(uow)
    return uow


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def presenter() -> EventPresenter:
    return EventPresenter(TIMEZONE)
