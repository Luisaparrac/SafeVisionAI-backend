"""Bounded doubly linked list with the most recent events (newest at head).

Adding goes at the head in O(1); when capacity is exceeded the tail is dropped
in O(1). A dict index gives O(1) access to a node to update its status.
"""
from dataclasses import dataclass
from typing import Any, Iterator


@dataclass
class _Node:
    event_id: int
    data: dict[str, Any]
    prev: "_Node | None" = None
    next: "_Node | None" = None


class EventHistory:
    def __init__(self, capacity: int = 100) -> None:
        self.capacity = capacity
        self._head: _Node | None = None
        self._tail: _Node | None = None
        self._index: dict[int, _Node] = {}

    def __len__(self) -> int:
        return len(self._index)

    def add_newest(self, event_id: int, data: dict[str, Any]) -> None:
        if event_id in self._index:
            self.update(event_id, data)
            return
        node = _Node(event_id, data, next=self._head)
        if self._head:
            self._head.prev = node
        self._head = node
        if self._tail is None:
            self._tail = node
        self._index[event_id] = node
        if len(self._index) > self.capacity:
            self._drop_tail()

    def add_oldest(self, event_id: int, data: dict[str, Any]) -> None:
        """Used when rebuilding from the database (rows come newest first)."""
        if event_id in self._index or len(self._index) >= self.capacity:
            return
        node = _Node(event_id, data, prev=self._tail)
        if self._tail:
            self._tail.next = node
        self._tail = node
        if self._head is None:
            self._head = node
        self._index[event_id] = node

    def update(self, event_id: int, data: dict[str, Any]) -> bool:
        node = self._index.get(event_id)
        if node is None:
            return False
        node.data = data
        return True

    def newest(self, limit: int) -> Iterator[dict[str, Any]]:
        node, count = self._head, 0
        while node and count < limit:
            yield node.data
            node, count = node.next, count + 1

    def oldest(self, limit: int) -> Iterator[dict[str, Any]]:
        node, count = self._tail, 0
        while node and count < limit:
            yield node.data
            node, count = node.prev, count + 1

    def _drop_tail(self) -> None:
        tail = self._tail
        if tail is None:
            return
        self._tail = tail.prev
        if self._tail:
            self._tail.next = None
        else:
            self._head = None
        del self._index[tail.event_id]
