"""PipelineFactory: a frozen dataclass describing a CI/CD pipeline provider."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


@dataclass(frozen=True)
class PipelineFactory:
    """Immutable description of a pipeline provider: where to write, what to render."""

    output_path: PurePosixPath
    template: str
    display_name: str
    description: str = ""

    def build(self, builder: ModuleBuilder) -> None:
        """Queue the pipeline file for creation via *builder*."""
        builder.add_rendered(
            builder.project_root / self.output_path,
            self.template,
            builder.base_context(),
        )
