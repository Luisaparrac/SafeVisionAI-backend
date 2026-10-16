from datetime import UTC, datetime, timedelta

from safevision.adapters.outbound.system_clock import SystemClock
from safevision.application.ports.clock import Clock


def test_satisfies_the_port():
    assert isinstance(SystemClock(), Clock)


def test_now_is_timezone_aware_utc_and_current():
    before = datetime.now(UTC)
    now = SystemClock().now()
    assert now.tzinfo is UTC
    assert before <= now <= datetime.now(UTC) + timedelta(seconds=1)
