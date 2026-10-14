"""Bounded doubly linked list with the most recent events, newest at the head.

New events enter at the head; when the capacity is exceeded the tail (the
oldest event) is dropped. A dictionary ``key -> node`` gives direct access to
any node so an event can be updated in place when its status changes.

Complexity (n = stored events, at most ``capacity``):

==============  ==========
Operation       Time
==============  ==========
add_newest      O(1)
add_oldest      O(1)
update          O(1)
contains / len  O(1)
newest(limit)   O(limit)
==============  ==========

Space: O(capacity).
"""


class _Node[V]:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int, value: V) -> None:
        self.key = key
        self.value = value
        self.prev: _Node[V] | None = None
        self.next: _Node[V] | None = None


class EventHistory[V]:
    def __init__(self, capacity: int) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.capacity = capacity
        self._head: _Node[V] | None = None
        self._tail: _Node[V] | None = None
        self._index: dict[int, _Node[V]] = {}

    def __len__(self) -> int:
        return len(self._index)

    def __contains__(self, key: object) -> bool:
        return key in self._index

    def add_newest(self, key: int, value: V) -> None:
        """Inserts at the head, dropping the oldest event if full.

        An existing key is updated in place instead of being duplicated. O(1).
        """
        if self.update(key, value):
            return
        node = _Node(key, value)
        node.next = self._head
        if self._head is not None:
            self._head.prev = node
        self._head = node
        if self._tail is None:
            self._tail = node
        self._index[key] = node
        if len(self._index) > self.capacity:
            self._drop_tail()

    def add_oldest(self, key: int, value: V) -> bool:
        """Appends at the tail; used to rebuild from rows sorted newest first.

        Returns False (and stores nothing) when full or the key exists. O(1).
        """
        if key in self._index or len(self._index) >= self.capacity:
            return False
        node = _Node(key, value)
        node.prev = self._tail
        if self._tail is not None:
            self._tail.next = node
        self._tail = node
        if self._head is None:
            self._head = node
        self._index[key] = node
        return True

    def update(self, key: int, value: V) -> bool:
        """Replaces the value of a stored event, keeping its position. O(1)."""
        node = self._index.get(key)
        if node is None:
            return False
        node.value = value
        return True

    def newest(self, limit: int) -> list[V]:
        """Up to ``limit`` values from the newest to the oldest. O(limit)."""
        values: list[V] = []
        node = self._head
        while node is not None and len(values) < limit:
            values.append(node.value)
            node = node.next
        return values

    def _drop_tail(self) -> None:
        tail = self._tail
        if tail is None:
            return
        self._tail = tail.prev
        if self._tail is not None:
            self._tail.next = None
        else:
            self._head = None
        del self._index[tail.key]
