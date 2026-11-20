"""Clock resource shared by adapters."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

import wireup


class Clock:
    """Wall clock with an explicit open/close lifecycle."""

    def now(self) -> datetime:
        return datetime.now(UTC)


@wireup.injectable
def open_clock() -> Iterator[Clock]:
    """Yield a clock for the application lifetime."""
    yield Clock()
