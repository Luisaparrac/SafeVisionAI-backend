import random
from datetime import timedelta

import pytest

from safevision.application.services.login_throttle import LoginThrottle
from tests.fakes.clock import FakeClock

WINDOW = timedelta(minutes=15)


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def throttle(clock) -> LoginThrottle:
    return LoginThrottle(clock.now)


@pytest.mark.parametrize(("max_failures", "window"), [(0, WINDOW), (5, timedelta(0))])
def test_invalid_limits(clock, max_failures, window):
    with pytest.raises(ValueError):
        LoginThrottle(clock.now, max_failures, window)


def test_blocked_from_the_fifth_failure(throttle):
    for _ in range(4):
        throttle.record_failure("a")
        assert not throttle.is_blocked("a")
    throttle.record_failure("a")
    assert throttle.is_blocked("a")
    assert not throttle.is_blocked("b")


def test_failures_leave_the_window(throttle, clock):
    for _ in range(5):
        throttle.record_failure("a")
        clock.advance(60)
    assert throttle.is_blocked("a")
    clock.advance(15 * 60 - 5 * 60)  # the first failure is exactly 15 minutes old
    assert not throttle.is_blocked("a")
    throttle.record_failure("a")
    assert throttle.is_blocked("a")


def test_forgotten_after_the_window(throttle, clock):
    throttle.record_failure("a")
    throttle.record_failure("b")
    assert len(throttle) == 2
    clock.advance(WINDOW.total_seconds())
    assert len(throttle) == 0


def test_clear_ignores_older_failures_when_they_expire(throttle, clock):
    for _ in range(3):
        throttle.record_failure("a")
    throttle.clear("a")
    clock.advance(60)
    throttle.record_failure("a")
    # The three cleared failures expire first and must not touch the new count.
    clock.advance(WINDOW.total_seconds() - 60)
    assert len(throttle) == 1
    for _ in range(4):
        throttle.record_failure("a")
    assert throttle.is_blocked("a")
    throttle.clear("missing")  # clearing an unknown e-mail is harmless


def test_matches_a_brute_force_count():
    # Random failures, clears and clock jumps against a naive list of instants.
    rng = random.Random(12)
    clock = FakeClock()
    throttle = LoginThrottle(clock.now, max_failures=3, window=timedelta(seconds=50))
    history: dict[str, list] = {}
    for _ in range(2000):
        email = rng.choice("abcd")
        action = rng.random()
        if action < 0.5:
            throttle.record_failure(email)
            history.setdefault(email, []).append(clock.now())
        elif action < 0.6:
            throttle.clear(email)
            history[email] = []
        else:
            clock.advance(rng.choice([1, 5, 20]))
        recent = [t for t in history.get(email, []) if clock.now() - t < timedelta(seconds=50)]
        assert throttle.is_blocked(email) == (len(recent) >= 3)
