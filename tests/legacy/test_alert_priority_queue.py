import random
from datetime import UTC, datetime, timedelta

from app.structures import AlertPriorityQueue
from app.structures.priority_queue import AlertEntry

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def entry(event_id: int, severity: int, minutes: int = 0) -> AlertEntry:
    return AlertEntry(
        event_id=event_id, severity=severity, created_at=BASE + timedelta(minutes=minutes)
    )


def test_empty_queue():
    queue = AlertPriorityQueue()
    assert len(queue) == 0
    assert queue.peek() is None
    assert queue.pop() is None
    assert queue.top(5) == []


def test_higher_severity_comes_first():
    queue = AlertPriorityQueue()
    for item in (entry(1, 1), entry(2, 4), entry(3, 2)):
        queue.push(item)
    assert [e.event_id for e in queue.top(3)] == [2, 3, 1]


def test_ties_are_broken_by_age_then_id():
    queue = AlertPriorityQueue()
    queue.push(entry(5, 3, minutes=10))
    queue.push(entry(4, 3, minutes=0))
    queue.push(entry(3, 3, minutes=10))
    assert [e.event_id for e in queue.top(3)] == [4, 3, 5]


def test_duplicate_push_is_ignored():
    queue = AlertPriorityQueue()
    queue.push(entry(1, 2))
    queue.push(entry(1, 4))
    assert len(queue) == 1
    assert queue.peek().severity == 2


def test_contains_and_remove_any_element():
    queue = AlertPriorityQueue()
    for i in range(1, 6):
        queue.push(entry(i, i % 4 + 1, minutes=i))
    assert 3 in queue
    assert queue.remove(3) is True
    assert 3 not in queue
    assert queue.remove(3) is False
    assert len(queue) == 4


def test_top_does_not_modify_the_queue():
    queue = AlertPriorityQueue()
    for i in range(10):
        queue.push(entry(i, i % 4 + 1, minutes=i))
    queue.top(3)
    assert len(queue) == 10


def test_pop_order_matches_sorted_order_after_random_operations():
    rng = random.Random(42)
    queue = AlertPriorityQueue()
    alive: dict[int, AlertEntry] = {}
    for i in range(300):
        item = entry(i, rng.randint(1, 4), minutes=rng.randint(0, 50))
        queue.push(item)
        alive[i] = item
        if rng.random() < 0.3:
            victim = rng.choice(list(alive))
            assert queue.remove(victim)
            del alive[victim]
    expected = sorted(alive.values(), key=lambda e: (-e.severity, e.created_at, e.event_id))
    popped = [queue.pop() for _ in range(len(queue))]
    assert popped == expected
