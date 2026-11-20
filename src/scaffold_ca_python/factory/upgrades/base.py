"""Upgrade action ABC."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory.upgrades.report import UpgradeResult


class UpgradeAction(ABC):
    """Single idempotent migration step run from ``scaffold up``."""

    name: ClassVar[str]
    description: ClassVar[str]

    @classmethod
    @abstractmethod
    def applies(cls, builder: ModuleBuilder) -> bool:
        """Return whether this action should run (content-based detection)."""

    @classmethod
    @abstractmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        """Apply upgrades through *builder* (queued ops persisted by the runner)."""
