"""In-memory board of pending alerts and recent events.

The database is the source of truth; the board is an index kept in sync by the
use cases and rebuilt from the database on startup. A lock makes each
operation atomic because the HTTP server handles requests in several threads.
"""

from threading import Lock

from safevision.application.dto import EventView
from safevision.domain.structures.alert_priority_queue import AlertEntry, AlertPriorityQueue
from safevision.domain.structures.event_history import EventHistory


class AlertBoard:
    def __init__(self, history_capacity: int) -> None:
        self._history_capacity = history_capacity
        self._queue = AlertPriorityQueue()
        self._history: EventHistory[EventView] = EventHistory(history_capacity)
        self._lock = Lock()

    @property
    def history_capacity(self) -> int:
        return self._history_capacity

    def add(self, entry: AlertEntry, view: EventView) -> None:
        """A new event with an open alert. O(log n)."""
        with self._lock:
            self._queue.push(entry)
            self._history.add_newest(view.id, view)

    def close(self, view: EventView) -> None:
        """The event left the pending state: its alert leaves the queue. O(log n)."""
        with self._lock:
            self._queue.remove(view.id)
            self._history.update(view.id, view)

    def pending(self, limit: int) -> list[AlertEntry]:
        """Most urgent pending alerts first. O(limit log limit)."""
        with self._lock:
            return self._queue.top(limit)

    def pending_count(self) -> int:
        with self._lock:
            return len(self._queue)

    def recent(self, limit: int) -> list[EventView]:
        """Most recent events first. O(limit)."""
        with self._lock:
            return self._history.newest(limit)

    def replace(self, pending: list[AlertEntry], recent_newest_first: list[EventView]) -> None:
        """Swaps the whole content at once (used when rebuilding from the database)."""
        queue = AlertPriorityQueue()
        for entry in pending:
            queue.push(entry)
        history: EventHistory[EventView] = EventHistory(self._history_capacity)
        for view in recent_newest_first:
            history.add_oldest(view.id, view)
        with self._lock:
            self._queue, self._history = queue, history
