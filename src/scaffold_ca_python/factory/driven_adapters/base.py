"""Base class for driven-adapter factories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class DrivenAdapterFactory(ABC):
    """Abstract base for driven-adapter factories."""

    fixed_name: ClassVar[str | None] = None

    def module_name(self, name: str | None) -> str | None:
        """Return the module directory name: fixed_name if set, else the user-supplied name."""
        return self.fixed_name or name

    @abstractmethod
    def build(self, builder: ModuleBuilder) -> None:
        """Populate *builder* with file and dependency operations."""
