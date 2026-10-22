"""Base classes for entry-point factories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, NamedTuple

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointFlag(Enum):
    """CLI flags that may be incompatible with certain entry-point types."""

    SWAGGER = ("--swagger", "is")
    ENABLE_MCP_CLIENT = ("--enable-mcp-client", "is")
    MCP_PRIMITIVES = ("--with-resources and --with-prompts", "are")
    ENABLE_KAFKA = ("--enable-kafka", "is")

    def __init__(self, label: str, verb: str) -> None:
        self.label = label
        self.verb = verb


class EntryPointConflict(NamedTuple):
    """A directory under infrastructure/entry_points/ whose presence blocks creation."""

    label: str
    subdir: str


class EntryPointFactory(ABC):
    """Abstract base for entry-point factories.

    Subclasses declare type-specific metadata as ClassVars so commands
    never need to know about individual types.
    """

    subdir: ClassVar[str]
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset()
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = ()

    @abstractmethod
    def build(self, builder: ModuleBuilder) -> None:
        """Populate *builder* with file and dependency operations."""

    def result_notes(
        self,
        project_root: Path,  # noqa: ARG002
        pkg: str,  # noqa: ARG002
        type_key: str,
        *,
        dry_run: bool,
    ) -> list[str]:
        """Return lines to display after creation.

        Default: the main.py replacement notice. Override for types that
        also update [project.scripts] (e.g. restapi).
        """
        verb = "will be replaced" if dry_run else "replaced"
        return [f"[yellow]⚠[/yellow] main.py {verb} with {type_key} entrypoint."]
