"""Upgrade action registry."""

from __future__ import annotations

from scaffold_ca_python.factory.upgrades.actions.upgrade_2026_11_20_dependency_injector_to_wireup import (
    UpgradeDependencyInjectorToWireup,
)
from scaffold_ca_python.factory.upgrades.base import UpgradeAction

UPGRADE_ACTIONS: list[type[UpgradeAction]] = [
    UpgradeDependencyInjectorToWireup,
]

__all__ = ["UPGRADE_ACTIONS", "UpgradeAction"]
