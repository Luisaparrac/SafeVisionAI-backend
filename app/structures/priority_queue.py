"""Max-heap of pending alerts, written by hand (no heapq).

Order: higher severity first; on ties, the oldest event first; then lower id.
A position index (id -> slot in the array) allows removing any alert in O(log n)
when it gets reviewed, not only the top one.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AlertEntry:
    event_id: int
    severity: int          # 3 Alto, 2 Medio, 1 Bajo
    created_at: datetime

    def outranks(self, other: "AlertEntry") -> bool:
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

    def __contains__(self, event_id: int) -> bool:
        return event_id in self._position

    def push(self, entry: AlertEntry) -> None:
        if entry.event_id in self._position:
            return
        self._heap.append(entry)
        index = len(self._heap) - 1
        self._position[entry.event_id] = index
        self._sift_up(index)

    def peek(self) -> AlertEntry | None:
        return self._heap[0] if self._heap else None

    def pop(self) -> AlertEntry | None:
        if not self._heap:
            return None
        return self._remove_at(0)

    def remove(self, event_id: int) -> bool:
        index = self._position.get(event_id)
        if index is None:
            return False
        self._remove_at(index)
        return True

    def top(self, k: int) -> list[AlertEntry]:
        """The k most urgent alerts, in order, without modifying the queue."""
        copy = AlertPriorityQueue()
        copy._heap = list(self._heap)
        copy._position = dict(self._position)
        result = []
        while len(result) < k and len(copy) > 0:
            result.append(copy.pop())
        return result

    def _remove_at(self, index: int) -> AlertEntry:
        removed = self._heap[index]
        last = self._heap.pop()
        del self._position[removed.event_id]
        if index < len(self._heap):
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
            if self._heap[index].outranks(self._heap[parent]):
                self._swap(index, parent)
                index = parent
            else:
                break

    def _sift_down(self, index: int) -> None:
        size = len(self._heap)
        while True:
            left, right, best = 2 * index + 1, 2 * index + 2, index
            if left < size and self._heap[left].outranks(self._heap[best]):
                best = left
            if right < size and self._heap[right].outranks(self._heap[best]):
                best = right
            if best == index:
                break
            self._swap(index, best)
            index = best
