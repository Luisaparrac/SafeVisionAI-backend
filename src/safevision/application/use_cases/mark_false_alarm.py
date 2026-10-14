"""Marks an event as a false alarm and dismisses its open alerts."""

from datetime import datetime

from safevision.application.use_cases._close_event import CloseEvent
from safevision.domain.errors import InvalidTransitionError
from safevision.domain.model.alert import Alert
from safevision.domain.model.event import Event
from safevision.domain.model.values import EventStatus


class MarkFalseAlarm(CloseEvent):
    """Repeating it is a no-op; a resolved event keeps its review result."""

    def _close_event(self, event: Event) -> None:
        event.mark_false_alarm()

    def _close_alert(self, alert: Alert, at: datetime) -> None:
        alert.dismiss(at)

    def _when_already_closed(self, event: Event) -> None:
        if event.status is not EventStatus.FALSE_ALARM:
            raise InvalidTransitionError(
                "Evento", event.status.value, EventStatus.FALSE_ALARM.value
            )
