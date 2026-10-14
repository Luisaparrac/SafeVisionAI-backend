import random
from datetime import datetime, timedelta

import pytest

from safevision.application.services.event_deduplicator import EventDeduplicator
from tests.fakes.clock import FakeClock

WINDOW = timedelta(seconds=30)
KEY = (1, 2, None)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def dedup(clock) -> EventDeduplicator:
    return EventDeduplicator(WINDOW, clock.now)


@pytest.mark.parametrize("window", [timedelta(seconds=-1), 30, None])
def test_invalid_window(window, clock):
    with pytest.raises(ValueError):
        EventDeduplicator(window, clock.now)


def test_unknown_key_is_not_a_duplicate(dedup):
    assert dedup.find_recent(KEY) is None


def test_repeat_inside_window_returns_first_event(dedup, clock):
    dedup.remember(KEY, 10)
    clock.advance(29.999)
    assert dedup.find_recent(KEY) == 10


def test_window_boundary_is_exclusive(dedup, clock):
    dedup.remember(KEY, 10)
    clock.advance(30)
    assert dedup.find_recent(KEY) is None
    assert len(dedup) == 0


def test_keys_are_independent(dedup):
    dedup.remember((1, 2, None), 10)
    assert dedup.find_recent((1, 2, 5)) is None
    assert dedup.find_recent((1, 3, None)) is None
    assert dedup.find_recent((2, 2, None)) is None


def test_lookups_do_not_extend_the_window(dedup, clock):
    dedup.remember(KEY, 10)
    for _ in range(5):
        clock.advance(10)
        dedup.find_recent(KEY)
    assert dedup.find_recent(KEY) is None


def test_remembering_again_restarts_the_window(dedup, clock):
    dedup.remember(KEY, 10)
    clock.advance(20)
    dedup.remember(KEY, 11)
    clock.advance(20)  # the first registration expired, the second did not
    assert dedup.find_recent(KEY) == 11
    assert len(dedup) == 1


def test_zero_window_never_deduplicates(clock):
    dedup = EventDeduplicator(timedelta(0), clock.now)
    dedup.remember(KEY, 10)
    assert dedup.find_recent(KEY) is None


def test_expired_keys_are_released(dedup, clock):
    for camera in range(100):
        dedup.remember((camera, 1, None), camera)
        clock.advance(1)
    clock.advance(30)
    assert len(dedup) == 0
    assert len(dedup._arrivals) == 0


@pytest.mark.parametrize("seed", range(5))
def test_random_sequence_matches_a_brute_force_model(seed, clock):
    rng = random.Random(seed)
    dedup = EventDeduplicator(WINDOW, clock.now)
    history: list[tuple[datetime, tuple, int]] = []
    for event_id in range(300):
        clock.advance(rng.choice([0, 0.5, 3, 12, 31]))
        key = (rng.randint(1, 3), rng.randint(1, 2), rng.choice([None, 7]))
        recent = [e for t, k, e in history if k == key and clock.now() - t < WINDOW]
        expected = recent[-1] if recent else None
        assert dedup.find_recent(key) == expected
        if expected is None:
            dedup.remember(key, event_id)
            history.append((clock.now(), key, event_id))
