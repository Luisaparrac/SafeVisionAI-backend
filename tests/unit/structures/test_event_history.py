import random

import pytest

from safevision.domain.structures.event_history import EventHistory


def filled(capacity: int, keys) -> EventHistory[str]:
    history: EventHistory[str] = EventHistory(capacity)
    for key in keys:
        history.add_newest(key, f"e{key}")
    return history


def assert_links(history: EventHistory) -> None:
    """Walking forward and backward visits the same nodes, matching the index."""
    forward, node = [], history._head
    while node is not None:
        forward.append(node.key)
        node = node.next
    backward, node = [], history._tail
    while node is not None:
        backward.append(node.key)
        node = node.prev
    assert forward == backward[::-1]
    assert sorted(forward) == sorted(history._index)


@pytest.mark.parametrize("capacity", [0, -1, 2.5, None, True])
def test_capacity_must_be_positive_integer(capacity):
    with pytest.raises(ValueError):
        EventHistory(capacity)


def test_empty_history():
    history: EventHistory[str] = EventHistory(3)
    assert len(history) == 0
    assert history.newest(5) == []
    assert history.update(1, "x") is False
    assert_links(history)


def test_newest_first_and_limit():
    history = filled(5, [1, 2, 3])
    assert history.newest(10) == ["e3", "e2", "e1"]
    assert history.newest(2) == ["e3", "e2"]
    assert history.newest(0) == []


def test_capacity_drops_oldest():
    history = filled(3, range(1, 6))
    assert len(history) == 3
    assert history.newest(10) == ["e5", "e4", "e3"]
    assert 1 not in history and 2 not in history
    assert_links(history)


def test_capacity_one():
    history = filled(1, [1, 2, 3])
    assert history.newest(5) == ["e3"]
    assert_links(history)


def test_update_keeps_position():
    history = filled(3, [1, 2, 3])
    assert history.update(2, "changed")
    assert history.newest(3) == ["e3", "changed", "e1"]


def test_add_newest_existing_key_updates_without_moving():
    history = filled(3, [1, 2])
    history.add_newest(1, "again")
    assert history.newest(3) == ["e2", "again"]
    assert len(history) == 2


def test_add_oldest_rebuilds_and_stops_at_capacity():
    history: EventHistory[str] = EventHistory(2)
    assert history.add_oldest(9, "e9")
    assert history.add_oldest(8, "e8")
    assert history.add_oldest(7, "e7") is False
    assert history.add_oldest(9, "dup") is False
    assert history.newest(5) == ["e9", "e8"]
    history.add_newest(10, "e10")
    assert history.newest(5) == ["e10", "e9"]
    assert_links(history)


@pytest.mark.parametrize("seed", range(10))
def test_random_operations_match_a_list_model(seed):
    rng = random.Random(seed)
    capacity = rng.randint(1, 8)
    history: EventHistory[int] = EventHistory(capacity)
    model: list[tuple[int, int]] = []  # newest first
    for step in range(300):
        key = rng.randint(1, 20)
        stored = [k for k, _ in model]
        if rng.random() < 0.7:
            history.add_newest(key, step)
            if key in stored:
                model[stored.index(key)] = (key, step)
            else:
                model = [(key, step), *model][:capacity]
        else:
            assert history.update(key, step) is (key in stored)
            if key in stored:
                model[stored.index(key)] = (key, step)
        assert history.newest(capacity) == [v for _, v in model]
        assert len(history) == len(model)
        assert_links(history)
