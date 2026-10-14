from safevision.application.ports.clock import Clock
from tests.fakes.clock import FakeClock


def test_fake_clock_satisfies_the_port_and_moves_on_demand():
    clock = FakeClock()
    assert isinstance(clock, Clock)
    start = clock.now()
    assert start.tzinfo is not None
    assert clock.now() == start
    clock.advance(1.5)
    assert (clock.now() - start).total_seconds() == 1.5
