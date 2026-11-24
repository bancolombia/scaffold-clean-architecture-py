"""Base classes for entry-point factories."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, NamedTuple

from rich.markup import escape

from scaffold_ca_python.core.project_detector import resolve_tests_root

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointFlag(Enum):
    """CLI flags that may be incompatible with certain entry-point types."""

    SWAGGER = ("--swagger", "is")
    MCP_PRIMITIVES = ("--with-resources and --with-prompts", "are")

    def __init__(self, label: str, verb: str) -> None:
        self.label = label
        self.verb = verb


class EntryPointConflict(NamedTuple):
    """Another entry-point type whose presence blocks creation of this one."""

    type_key: str


class EntryPointFactory(ABC):
    """Abstract base for entry-point factories.

    Subclasses declare type-specific metadata as ClassVars so commands
    never need to know about individual types.
    """

    description: ClassVar[str] = ""
    subdir: ClassVar[str]
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset()
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = ()

    @classmethod
    def entry_points_src(cls, builder: ModuleBuilder) -> Path:
        """Source tree path for this entry-point type under infrastructure/entry_points/."""
        return builder.project_ctx.src_pkg_root.joinpath("infrastructure", "entry_points", *cls.subdir.split("/"))

    @classmethod
    def entry_points_tests(cls, builder: ModuleBuilder) -> Path:
        """Test mirror path for this entry-point type."""
        rel = Path("infrastructure", "entry_points", *cls.subdir.split("/"))
        return resolve_tests_root(builder.project_root) / rel

    @classmethod
    def pkg_file(cls, builder: ModuleBuilder, *parts: str) -> Path:
        """Path under the project package root (src/<pkg>/...)."""
        return builder.project_ctx.src_pkg_root.joinpath(*parts)

    @abstractmethod
    def build(self, builder: ModuleBuilder) -> None:
        """Populate *builder* with file and dependency operations."""

    def result_notes(
        self,
        src_pkg_root: Path,
        pkg: str,
        type_key: str,
        *,
        dry_run: bool,
    ) -> list[str]:
        """Return lines to display after creation.

        Default: the main.py replacement notice. Override for types that
        also update [project.scripts] (e.g. restapi).
        """
        del src_pkg_root, pkg
        verb = "will be replaced" if dry_run else "replaced"
        return [f"[yellow]⚠[/yellow] main.py {verb} with {type_key} entrypoint."]


def server_entry_notes(src_pkg_root: Path, pkg: str, entry_fn: str, *, dry_run: bool) -> list[str]:
    """Notes for types whose server.py replaces main.py and owns [project.scripts]."""
    scripts = escape("[project.scripts]")
    target = f'{pkg} = "{pkg}.server:{entry_fn}"'
    if dry_run:
        notes = [f"[dim]Would delete: src/{pkg}/main.py[/dim]"] if (src_pkg_root / "main.py").exists() else []
        return [*notes, f"[dim]Would update {scripts}: {target}[/dim]"]
    return [f"[green]✓[/green] Deleted src/{pkg}/main.py", f"[green]✓[/green] Updated {scripts}: {target}"]
