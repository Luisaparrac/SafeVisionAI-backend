from datetime import UTC, datetime, timedelta


class FakeClock:
    """Clock that only moves when the test says so."""

    def __init__(self, start: datetime = datetime(2026, 10, 14, 12, 0, tzinfo=UTC)) -> None:
        self.current = start

    def now(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)
