from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from safevision.application.dto import CameraCount, EventTypeCount
from safevision.application.use_cases.get_statistics import (
    GetCameraStatistics,
    GetEventTypeStatistics,
)
from safevision.domain.errors import ValidationError
from safevision.domain.model.event import Event

BOGOTA = ZoneInfo("America/Bogota")


@pytest.fixture
def uow(uow):
    # Two Ruido and one Caída on camera 1 on the 14th (local), one Humo on camera 2 on the 15th.
    for camera_id, event_type_id, day in [(1, 3, 14), (1, 3, 14), (1, 1, 14), (2, 4, 15)]:
        occurred = datetime(2026, 10, day, 23, 30, tzinfo=BOGOTA)
        uow.events.add(
            Event(camera_id=camera_id, event_type_id=event_type_id, occurred_at=occurred)
        )
    uow.commit()
    return uow


def test_counts_per_type_include_types_without_events(uow):
    assert GetEventTypeStatistics(uow, BOGOTA).execute() == [
        EventTypeCount(3, "Ruido", "Bajo", 2),
        EventTypeCount(1, "Caída", "Alto", 1),
        EventTypeCount(4, "Humo", "Alto", 1),
        EventTypeCount(2, "Merodeo", "Medio", 0),
    ]


def test_counts_per_camera(uow):
    assert GetCameraStatistics(uow, BOGOTA).execute() == [
        CameraCount(1, "Sala", 3),
        CameraCount(2, "Patio", 1),
    ]


def test_date_filters_use_local_days(uow):
    # 23:30 in Bogotá on the 15th is already the 16th in UTC: it still counts as the 15th.
    on_15 = GetCameraStatistics(uow, BOGOTA).execute(date(2026, 10, 15), date(2026, 10, 15))
    assert on_15 == [CameraCount(2, "Patio", 1), CameraCount(1, "Sala", 0)]
    until_14 = GetEventTypeStatistics(uow, BOGOTA).execute(date_to=date(2026, 10, 14))
    assert [(row.name, row.total) for row in until_14 if row.total] == [("Ruido", 2), ("Caída", 1)]


def test_reversed_range(uow):
    with pytest.raises(ValidationError):
        GetEventTypeStatistics(uow, BOGOTA).execute(date(2026, 10, 15), date(2026, 10, 14))
