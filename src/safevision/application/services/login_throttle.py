"""Sliding time window that limits failed logins per e-mail.

An e-mail with ``max_failures`` failed logins in the last ``window`` is
blocked until the oldest of them leaves the window. A successful login clears
its count.

Two structures work together, as in the event deduplicator:

* a ``LinkedQueue`` with ``(email, generation, failed_at)`` in arrival order,
  so expired failures are always at the front and are discarded in O(1) each;
* a dictionary ``email -> (generation, failures)`` with the failures of each
  e-mail still inside the window, for O(1) checks.

A cleared e-mail leaves its old failures in the queue. Each new count gets a
new generation number, so when those entries expire they no longer match the
dictionary and are simply skipped.

Complexity: every operation is amortized O(1), because every failure is
enqueued and dequeued once. Space: O(failures in the window), so e-mails that
stop failing are forgotten on their own. The state lives in memory: it is per
process and starts empty after a restart.
"""

from collections.abc import Callable
from datetime import datetime, timedelta
from threading import Lock

from safevision.domain.structures.linked_queue import LinkedQueue

MAX_FAILURES = 5
WINDOW = timedelta(minutes=15)


class LoginThrottle:
    def __init__(
        self,
        clock: Callable[[], datetime],
        max_failures: int = MAX_FAILURES,
        window: timedelta = WINDOW,
    ) -> None:
        if max_failures < 1 or window <= timedelta(0):
            raise ValueError("max_failures and window must be positive")
        self._clock = clock
        self._max_failures = max_failures
        self._window = window
        self._failures: LinkedQueue[tuple[str, int, datetime]] = LinkedQueue()
        self._counts: dict[str, tuple[int, int]] = {}
        self._generation = 0
        self._lock = Lock()

    def __len__(self) -> int:
        """E-mails with failures inside the window."""
        with self._lock:
            self._expire(self._clock())
            return len(self._counts)

    def is_blocked(self, email: str) -> bool:
        with self._lock:
            self._expire(self._clock())
            _, failures = self._counts.get(email, (0, 0))
            return failures >= self._max_failures

    def record_failure(self, email: str) -> None:
        with self._lock:
            now = self._clock()
            self._expire(now)
            if email in self._counts:
                generation, failures = self._counts[email]
            else:
                self._generation += 1
                generation, failures = self._generation, 0
            self._counts[email] = (generation, failures + 1)
            self._failures.enqueue((email, generation, now))

    def clear(self, email: str) -> None:
        with self._lock:
            self._counts.pop(email, None)

    def _expire(self, now: datetime) -> None:
        while self._failures and now - self._failures.peek()[2] >= self._window:
            email, generation, _ = self._failures.dequeue()
            current = self._counts.get(email)
            if current is None or current[0] != generation:
                continue  # cleared after this failure
            if current[1] == 1:
                del self._counts[email]
            else:
                self._counts[email] = (generation, current[1] - 1)
