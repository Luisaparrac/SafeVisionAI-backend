from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest

from safevision.application.date_range import local_day_range
from safevision.domain.errors import ValidationError

BOGOTA = ZoneInfo("America/Bogota")


def test_both_ends():
    start, end = local_day_range(date(2026, 10, 14), date(2026, 10, 15), BOGOTA)
    assert start == datetime(2026, 10, 14, tzinfo=BOGOTA)
    assert end == datetime(2026, 10, 16, tzinfo=BOGOTA)


def test_open_ends():
    assert local_day_range(None, None, BOGOTA) == (None, None)
    assert local_day_range(date(2026, 10, 14), None, BOGOTA)[1] is None
    assert local_day_range(None, date(2026, 10, 14), BOGOTA)[0] is None


def test_single_day_covers_24_hours():
    start, end = local_day_range(date(2026, 10, 14), date(2026, 10, 14), BOGOTA)
    assert (end - start).total_seconds() == 24 * 3600


def test_reversed_range():
    with pytest.raises(ValidationError):
        local_day_range(date(2026, 10, 15), date(2026, 10, 14), BOGOTA)
