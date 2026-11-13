"""EntryPointOptions: typed, frozen parameter object for the gep command."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

_FLAG_ORDER = ("swagger", "with_resources", "with_prompts")
_FLAG_LABELS = {
    "swagger": "--swagger",
    "with_resources": "--with-resources",
    "with_prompts": "--with-prompts",
}


@dataclass(frozen=True, slots=True)
class EntryPointOptions:
    """Immutable snapshot of all CLI options for a single gep invocation."""

    type_: str
    swagger: str | None = None
    with_resources: bool = False
    with_prompts: bool = False
    add_tool: bool = False
    name: str | None = None
    params: tuple[str, ...] = field(default_factory=tuple)
    returns: str = "str"
    description: str | None = None
    dry_run: bool = False

    def creation_flags(self) -> list[str]:
        """Return active flag strings in canonical display order."""
        result: list[str] = []
        for attr in _FLAG_ORDER:
            val = getattr(self, attr)
            if val:
                result.append(_FLAG_LABELS[attr])
        return result

    def apply_to(self, builder: ModuleBuilder, routes: list[tuple[str, str]]) -> None:
        """Transfer per-type options into *builder* parameters."""
        builder.add_param("routes", routes)
        builder.add_param("with_resources", self.with_resources)
        builder.add_param("with_prompts", self.with_prompts)
