from datetime import UTC, datetime, timedelta

import pytest

from safevision.domain.model.values import Severity
from safevision.domain.structures.alert_priority_queue import AlertEntry, AlertPriorityQueue

BASE = datetime(2026, 1, 1, tzinfo=UTC)


def entry(event_id: int, severity: int, minutes: int = 0) -> AlertEntry:
    return AlertEntry(event_id, Severity(severity), BASE + timedelta(minutes=minutes))


def ids(entries) -> list[int]:
    return [e.event_id for e in entries]


def test_empty_queue():
    queue = AlertPriorityQueue()
    assert len(queue) == 0
    assert queue.peek() is None
    assert queue.pop() is None
    assert queue.top(3) == []
    assert queue.remove(1) is False


def test_single_element():
    queue = AlertPriorityQueue()
    assert queue.push(entry(1, 2)) is True
    assert queue.peek() == entry(1, 2)
    assert queue.pop() == entry(1, 2)
    assert len(queue) == 0


def test_higher_severity_first():
    queue = AlertPriorityQueue()
    for item in (entry(1, 1), entry(2, 4), entry(3, 2), entry(4, 3)):
        queue.push(item)
    assert ids(queue.top(4)) == [2, 4, 3, 1]


def test_ties_broken_by_age_then_event_id():
    queue = AlertPriorityQueue()
    queue.push(entry(5, 3, minutes=10))
    queue.push(entry(4, 3, minutes=0))
    queue.push(entry(3, 3, minutes=10))
    assert ids(queue.top(3)) == [4, 3, 5]


def test_duplicate_event_is_rejected():
    queue = AlertPriorityQueue()
    assert queue.push(entry(1, 2))
    assert queue.push(entry(1, 4)) is False
    assert len(queue) == 1
    assert queue.peek().severity == Severity(2)


def test_remove_top_middle_and_last():
    queue = AlertPriorityQueue()
    for i in range(1, 8):
        queue.push(entry(i, 4 - i % 4, minutes=i))
    order = ids(queue.top(7))
    for victim in (order[0], order[3], order[-1]):
        assert queue.remove(victim)
        assert victim not in queue
    expected = [i for i in order if i not in (order[0], order[3], order[-1])]
    assert ids(queue.pop() for _ in range(len(queue))) == expected


@pytest.mark.parametrize("k", [0, -1])
def test_top_with_non_positive_k(k):
    queue = AlertPriorityQueue()
    queue.push(entry(1, 1))
    assert queue.top(k) == []


def test_top_larger_than_size_and_does_not_modify():
    queue = AlertPriorityQueue()
    for i in range(5):
        queue.push(entry(i, i % 4 + 1))
    assert len(queue.top(50)) == 5
    assert len(queue) == 5
    assert all(i in queue for i in range(5))


def test_reinsert_after_removal():
    queue = AlertPriorityQueue()
    queue.push(entry(1, 1))
    queue.remove(1)
    assert queue.push(entry(1, 4))
    assert queue.peek().severity == Severity(4)
