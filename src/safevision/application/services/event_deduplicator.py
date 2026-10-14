"""Sliding time window that recognizes repeated detections from the IoT module.

The camera keeps reporting the same situation several times per second. A
detection is a duplicate when the same ``(camera_id, event_type_id,
subject_id)`` was registered less than ``window`` ago.

Two structures work together:

* a ``LinkedQueue`` with ``(key, registered_at)`` in arrival order, so expired
  registrations are always at the front and are discarded in O(1) each;
* a dictionary ``key -> (registered_at, event_id)`` with the latest
  registration of each key, for O(1) lookups.

A key registered again leaves an older entry in the queue; when that entry
expires it no longer matches the dictionary and is simply skipped.

Complexity: ``find_recent`` and ``remember`` are amortized O(1), because every
queue entry is enqueued and dequeued once. Space: O(registrations in the window).
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from threading import Lock

from safevision.domain.structures.linked_queue import LinkedQueue

DedupKey = tuple[int, int, int | None]


class EventDeduplicator:
    def __init__(self, window: timedelta, clock: Callable[[], datetime]) -> None:
        if not isinstance(window, timedelta) or window < timedelta(0):
            raise ValueError("window must be a non-negative timedelta")
        self._window = window
        self._clock = clock
        self._arrivals: LinkedQueue[tuple[DedupKey, datetime]] = LinkedQueue()
        self._latest: dict[DedupKey, tuple[datetime, int]] = {}
        self._lock = Lock()

    def __len__(self) -> int:
        """Keys currently inside the window."""
        with self._lock:
            self._expire(self._clock())
            return len(self._latest)

    def find_recent(self, key: DedupKey) -> int | None:
        """Event id registered for ``key`` inside the window, or None."""
        with self._lock:
            now = self._clock()
            self._expire(now)
            latest = self._latest.get(key)
            if latest is None or now - latest[0] >= self._window:
                return None
            return latest[1]

    def remember(self, key: DedupKey, event_id: int) -> None:
        """Records that ``key`` produced ``event_id`` now.

        Called only after the event was stored, so a failed registration never
        hides a later retry.
        """
        with self._lock:
            now = self._clock()
            self._expire(now)
            self._latest[key] = (now, event_id)
            self._arrivals.enqueue((key, now))

    def _expire(self, now: datetime) -> None:
        while self._arrivals and now - self._arrivals.peek()[1] >= self._window:
            key, registered_at = self._arrivals.dequeue()
            latest = self._latest.get(key)
            if latest is not None and latest[0] == registered_at:
                del self._latest[key]
