"""Clock adapter backed by the operating system time."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        """Current instant in UTC; the presenter converts it to the configured time zone."""
        return datetime.now(UTC)
