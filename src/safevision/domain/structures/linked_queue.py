"""FIFO queue built on a singly linked list (no deque, no queue module).

The queue keeps a pointer to the front node (next to leave) and to the back
node (last to arrive), so both ends are reached without walking the list.

Complexity (n = queued items):

==============  ======
Operation       Time
==============  ======
enqueue         O(1)
dequeue         O(1)
peek            O(1)
len / bool      O(1)
==============  ======

Space: O(n).
"""


class _Node[T]:
    __slots__ = ("value", "next")

    def __init__(self, value: T) -> None:
        self.value = value
        self.next: _Node[T] | None = None


class LinkedQueue[T]:
    def __init__(self) -> None:
        self._front: _Node[T] | None = None
        self._back: _Node[T] | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def __bool__(self) -> bool:
        return self._size > 0

    def enqueue(self, value: T) -> None:
        """Adds a value at the back. O(1)."""
        node = _Node(value)
        if self._back is None:
            self._front = node
        else:
            self._back.next = node
        self._back = node
        self._size += 1

    def peek(self) -> T:
        """Value at the front without removing it. O(1)."""
        if self._front is None:
            raise IndexError("peek from an empty queue")
        return self._front.value

    def dequeue(self) -> T:
        """Removes and returns the value at the front. O(1)."""
        if self._front is None:
            raise IndexError("dequeue from an empty queue")
        node = self._front
        self._front = node.next
        if self._front is None:
            self._back = None
        self._size -= 1
        return node.value
