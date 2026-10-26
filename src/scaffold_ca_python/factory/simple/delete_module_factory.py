"""DeleteModuleFactory implementation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from scaffold_ca_python.core.module_locator import find_module_targets
from scaffold_ca_python.core.name_utils import to_snake_case
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class DeleteModuleFactory(ModuleFactory):
    """Factory for module deletion."""

    def build(self, builder: ModuleBuilder) -> None:
        """Build deletion operations for a module.

        Finds and deletes modules across:
        - domain/model/<snake>/ (package) or domain/model/<snake>.py (legacy)
        - domain/usecase/<snake>.py
        - infrastructure/driven_adapters/<snake>/
        - infrastructure/entry_points/<snake>/
        - infrastructure/helpers/<snake>/
        """
        project_root = builder.project_root
        pkg = builder.project_ctx.python_package

        # Get module name and convert to snake_case
        module_name = builder.module_ctx.name if builder.module_ctx else "Module"
        snake_name = to_snake_case(module_name)

        candidates = find_module_targets(project_root, pkg, snake_name)

        if not builder.dry_run:
            for src_path, test_path in candidates:
                self._delete_path(src_path)
                if test_path:
                    self._delete_path(test_path)

    @staticmethod
    def _delete_path(path: Path) -> None:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
