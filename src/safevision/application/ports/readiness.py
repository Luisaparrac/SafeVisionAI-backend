"""Readiness port: whether the infrastructure the application needs can be reached."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReadinessProbe(Protocol):
    def is_ready(self) -> bool:
        """True when requests can be served; never raises."""
        ...
