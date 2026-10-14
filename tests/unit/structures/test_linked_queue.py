import random

import pytest

from safevision.domain.structures.linked_queue import LinkedQueue


def test_empty_queue():
    queue: LinkedQueue[int] = LinkedQueue()
    assert len(queue) == 0
    assert not queue
    with pytest.raises(IndexError):
        queue.peek()
    with pytest.raises(IndexError):
        queue.dequeue()


def test_first_in_first_out():
    queue: LinkedQueue[str] = LinkedQueue()
    for value in "abc":
        queue.enqueue(value)
    assert queue.peek() == "a"
    assert [queue.dequeue() for _ in range(3)] == ["a", "b", "c"]
    assert not queue


def test_reusable_after_becoming_empty():
    queue: LinkedQueue[int] = LinkedQueue()
    queue.enqueue(1)
    queue.dequeue()
    queue.enqueue(2)
    queue.enqueue(3)
    assert queue.peek() == 2
    assert len(queue) == 2


def test_none_is_a_valid_value():
    queue: LinkedQueue[None] = LinkedQueue()
    queue.enqueue(None)
    assert queue
    assert queue.dequeue() is None


@pytest.mark.parametrize("seed", range(10))
def test_random_operations_match_a_list_model(seed):
    rng = random.Random(seed)
    queue: LinkedQueue[int] = LinkedQueue()
    model: list[int] = []
    for step in range(500):
        if rng.random() < 0.55 or not model:
            queue.enqueue(step)
            model.append(step)
        else:
            assert queue.dequeue() == model.pop(0)
        assert len(queue) == len(model)
        if model:
            assert queue.peek() == model[0]
