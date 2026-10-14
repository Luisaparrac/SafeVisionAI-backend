"""Property tests: random operations with fixed seeds, checked against a sorted list."""

import random
from datetime import UTC, datetime, timedelta

import pytest

from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry, AlertPriorityQueue

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def rank(entry: AlertEntry):
    return (-entry.severity.level, entry.created_at, entry.event_id)


def random_entry(rng: random.Random, event_id: int) -> AlertEntry:
    # Few distinct times so ties on severity and age happen often.
    return AlertEntry(
        event_id, Severity(rng.randint(1, 4)), BASE + timedelta(minutes=rng.randint(0, 5))
    )


def assert_invariants(queue: AlertPriorityQueue) -> None:
    heap, position = queue._heap, queue._position
    assert len(position) == len(heap)
    for index, entry in enumerate(heap):
        assert position[entry.event_id] == index
        for child in (2 * index + 1, 2 * index + 2):
            if child < len(heap):
                assert not heap[child].outranks(entry)


@pytest.mark.parametrize("seed", range(10))
def test_random_operations_keep_the_most_urgent_on_top(seed):
    rng = random.Random(seed)
    queue = AlertPriorityQueue()
    model: dict[int, AlertEntry] = {}
    next_id = 1
    for _ in range(400):
        operation = rng.random()
        if operation < 0.5 or not model:
            item = random_entry(rng, next_id)
            next_id += 1
            assert queue.push(item)
            model[item.event_id] = item
        elif operation < 0.75:
            victim = rng.choice(list(model))
            assert queue.remove(victim)
            del model[victim]
        elif operation < 0.9:
            expected = min(model.values(), key=rank)
            assert queue.pop() == expected
            del model[expected.event_id]
        else:
            k = rng.randint(0, 10)
            assert queue.top(k) == sorted(model.values(), key=rank)[:k]
        assert len(queue) == len(model)
        assert queue.peek() == (min(model.values(), key=rank) if model else None)
        assert_invariants(queue)


@pytest.mark.parametrize("seed", range(5))
def test_draining_returns_everything_in_priority_order(seed):
    rng = random.Random(seed)
    queue = AlertPriorityQueue()
    items = [random_entry(rng, i) for i in range(1, 201)]
    for item in items:
        queue.push(item)
    drained = [queue.pop() for _ in range(len(items))]
    assert drained == sorted(items, key=rank)
    assert len(queue) == 0


def test_removing_unknown_ids_never_changes_the_queue():
    rng = random.Random(99)
    queue = AlertPriorityQueue()
    for i in range(1, 51):
        queue.push(random_entry(rng, i))
    before = queue.top(50)
    for unknown in (0, 51, 1000):
        assert queue.remove(unknown) is False
    assert queue.top(50) == before
    assert_invariants(queue)
