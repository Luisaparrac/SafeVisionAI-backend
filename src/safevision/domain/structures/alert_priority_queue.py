"""Max-heap of pending alerts with a position index, written by hand (no heapq).

Ordering is total and deterministic: higher severity first; on ties, the
oldest alert first; then the lowest event id.

The heap lives in an array where the children of slot ``i`` are ``2i + 1`` and
``2i + 2``. A dictionary ``event_id -> slot`` lets the queue remove any alert,
not only the top one, when its event gets reviewed.

Complexity (n = alerts in the queue):

=================  ==========
Operation          Time
=================  ==========
push               O(log n)
peek               O(1)
pop                O(log n)
remove(event_id)   O(log n)
contains / len     O(1)
top(k)             O(k log n)
=================  ==========

Space: O(n) for the array plus O(n) for the position index.
"""

from dataclasses import dataclass
from datetime import datetime

from safevision.domain.model.values import Severity


@dataclass(frozen=True)
class AlertEntry:
    """What the queue needs to know about a pending alert."""

    event_id: int
    severity: Severity
    created_at: datetime

    def outranks(self, other: "AlertEntry") -> bool:
        """True when this alert must be attended before ``other``."""
        if self.severity != other.severity:
            return self.severity > other.severity
        if self.created_at != other.created_at:
            return self.created_at < other.created_at
        return self.event_id < other.event_id


class AlertPriorityQueue:
    def __init__(self) -> None:
        self._heap: list[AlertEntry] = []
        self._position: dict[int, int] = {}

    def __len__(self) -> int:
        return len(self._heap)

    def __contains__(self, event_id: object) -> bool:
        return event_id in self._position

    def push(self, entry: AlertEntry) -> bool:
        """Adds the alert; returns False if its event is already queued. O(log n)."""
        if entry.event_id in self._position:
            return False
        self._heap.append(entry)
        index = len(self._heap) - 1
        self._position[entry.event_id] = index
        self._sift_up(index)
        return True

    def peek(self) -> AlertEntry | None:
        """Most urgent alert without removing it. O(1)."""
        return self._heap[0] if self._heap else None

    def pop(self) -> AlertEntry | None:
        """Removes and returns the most urgent alert. O(log n)."""
        return self._remove_at(0) if self._heap else None

    def remove(self, event_id: int) -> bool:
        """Removes the alert of an event wherever it is. O(log n)."""
        index = self._position.get(event_id)
        if index is None:
            return False
        self._remove_at(index)
        return True

    def top(self, k: int) -> list[AlertEntry]:
        """The k most urgent alerts in order, leaving the queue untouched. O(k log n)."""
        copy = AlertPriorityQueue()
        copy._heap = list(self._heap)
        copy._position = dict(self._position)
        result: list[AlertEntry] = []
        while len(result) < k and copy._heap:
            result.append(copy._remove_at(0))
        return result

    def _remove_at(self, index: int) -> AlertEntry:
        removed = self._heap[index]
        last = self._heap.pop()
        del self._position[removed.event_id]
        if index < len(self._heap):
            # The last element fills the hole and moves up or down as needed.
            self._heap[index] = last
            self._position[last.event_id] = index
            self._sift_up(index)
            self._sift_down(self._position[last.event_id])
        return removed

    def _swap(self, i: int, j: int) -> None:
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._position[self._heap[i].event_id] = i
        self._position[self._heap[j].event_id] = j

    def _sift_up(self, index: int) -> None:
        while index > 0:
            parent = (index - 1) // 2
            if not self._heap[index].outranks(self._heap[parent]):
                return
            self._swap(index, parent)
            index = parent

    def _sift_down(self, index: int) -> None:
        size = len(self._heap)
        while True:
            best = index
            for child in (2 * index + 1, 2 * index + 2):
                if child < size and self._heap[child].outranks(self._heap[best]):
                    best = child
            if best == index:
                return
            self._swap(index, best)
            index = best
