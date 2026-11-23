"""Tests for the clock helper."""

from legacy_fixture.infrastructure.helpers.clock.clock import Clock, open_clock


def test_open_clock_yields_clock() -> None:
    assert isinstance(next(open_clock()), Clock)
