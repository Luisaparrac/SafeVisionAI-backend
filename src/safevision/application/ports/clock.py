"""Clock port: the application never reads the system time directly."""

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    def now(self) -> datetime:
        """Current instant, timezone-aware."""
        ...
