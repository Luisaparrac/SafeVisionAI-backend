"""Notifier port: pushes alert changes to whoever is listening (the panel)."""

from typing import Protocol, runtime_checkable

from safevision.application.dto import AlertNotification


@runtime_checkable
class AlertNotifier(Protocol):
    def publish(self, notification: AlertNotification) -> None:
        """Best effort and non-blocking; never raises, even with nobody listening."""
        ...
