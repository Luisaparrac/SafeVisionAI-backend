"""Sliding time window that limits how often one key (an e-mail, an address) acts.

A key with ``limit`` uses in the last ``window`` is blocked until the oldest of
them leaves the window. Clearing a key forgets its uses.

Two structures work together, as in the event deduplicator:

* a ``LinkedQueue`` with ``(key, generation, used_at)`` in arrival order, so
  expired uses are always at the front and are discarded in O(1) each;
* a dictionary ``key -> (generation, uses)`` with the uses of each key still
  inside the window, for O(1) checks.

A cleared key leaves its old uses in the queue. Each new count gets a new
generation number, so when those entries expire they no longer match the
dictionary and are simply skipped.

Complexity: every operation is amortized O(1), because every use is enqueued
and dequeued once. Space: O(uses in the window), so keys that stop acting are
forgotten on their own. The state lives in memory: it is per process and starts
empty after a restart.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from threading import Lock

from safevision.domain.structures.linked_queue import LinkedQueue


class SlidingWindowLimiter:
    def __init__(self, clock: Callable[[], datetime], limit: int, window: timedelta) -> None:
        if limit < 1 or window <= timedelta(0):
            raise ValueError("limit and window must be positive")
        self._clock = clock
        self._limit = limit
        self._window = window
        self._uses: LinkedQueue[tuple[str, int, datetime]] = LinkedQueue()
        self._counts: dict[str, tuple[int, int]] = {}
        self._generation = 0
        self._lock = Lock()

    def __len__(self) -> int:
        """Keys with uses inside the window."""
        with self._lock:
            self._expire(self._clock())
            return len(self._counts)

    def is_blocked(self, key: str) -> bool:
        with self._lock:
            self._expire(self._clock())
            _, uses = self._counts.get(key, (0, 0))
            return uses >= self._limit

    def record(self, key: str) -> None:
        with self._lock:
            now = self._clock()
            self._expire(now)
            if key in self._counts:
                generation, uses = self._counts[key]
            else:
                self._generation += 1
                generation, uses = self._generation, 0
            self._counts[key] = (generation, uses + 1)
            self._uses.enqueue((key, generation, now))

    def clear(self, key: str) -> None:
        with self._lock:
            self._counts.pop(key, None)

    def _expire(self, now: datetime) -> None:
        while self._uses and now - self._uses.peek()[2] >= self._window:
            key, generation, _ = self._uses.dequeue()
            current = self._counts.get(key)
            if current is None or current[0] != generation:
                continue  # cleared after this use
            if current[1] == 1:
                del self._counts[key]
            else:
                self._counts[key] = (generation, current[1] - 1)
