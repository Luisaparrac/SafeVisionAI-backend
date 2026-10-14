"""Marks an event as reviewed (resolved) and closes its open alerts."""

from datetime import datetime

from safevision.application.use_cases._close_event import CloseEvent
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event


class ReviewEvent(CloseEvent):
    """Idempotent: reviewing an already closed event returns it unchanged."""

    def _close_event(self, event: Event) -> None:
        event.resolve()

    def _close_alert(self, alert: Alert, at: datetime) -> None:
        alert.close(at)
