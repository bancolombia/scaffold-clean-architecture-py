"""DeleteModuleFactory implementation."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from scaffold_ca_python.core.module_locator import find_module_targets
from scaffold_ca_python.core.name_utils import to_snake_case
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import remove_test_function
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class DeleteModuleFactory(ModuleFactory):
    """Factory for module deletion."""

    def build(self, builder: ModuleBuilder) -> None:
        """Build deletion operations for a module.

        Finds and deletes modules across:
        - domain/model/<snake>/ (package) or domain/model/<snake>.py (legacy)
        - domain/usecase/<base>_usecase.py or domain/usecase/<snake>.py (legacy)
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

        tests_root = resolve_tests_root(project_root)
        factory_path = project_root / "src" / pkg / "application" / "config" / "usecases" / f"{snake_name}_usecase.py"
        factory_test_path = tests_root / "application" / "config" / "usecases" / f"test_{snake_name}_usecase.py"
        wiring_test_path = tests_root / "application" / "config" / "test_wiring.py"
        wiring_fn_name = f"test_container_resolves_{snake_name}_usecase"

        if not builder.dry_run:
            for src_path, test_path in candidates:
                self._delete_path(src_path)
                if test_path:
                    self._delete_path(test_path)
            if factory_path.exists():
                factory_path.unlink()
            if factory_test_path.exists():
                factory_test_path.unlink()
            if wiring_test_path.exists():
                updated = remove_test_function(wiring_test_path.read_text(encoding="utf-8"), wiring_fn_name)
                if updated is not None:
                    wiring_test_path.write_text(updated, encoding="utf-8")

    @staticmethod
    def _delete_path(path: Path) -> None:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
