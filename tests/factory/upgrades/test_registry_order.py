"""Registry ordering for upgrade actions."""

from __future__ import annotations

import re
from datetime import datetime

from scaffold_ca_python.factory.upgrades import UPGRADE_ACTIONS


def test_upgrade_action_module_dates_non_decreasing() -> None:
    dates: list[datetime] = []
    pattern = re.compile(r"upgrade_(\d{4})_(\d{2})_(\d{2})_")
    for action_cls in UPGRADE_ACTIONS:
        module = action_cls.__module__.split(".")[-1]
        match = pattern.search(module)
        assert match, f"module {module} missing dated prefix"
        y, m, d = (int(x) for x in match.groups())
        dates.append(datetime(y, m, d))
    assert dates == sorted(dates)
