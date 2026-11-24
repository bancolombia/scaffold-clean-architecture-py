from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from scaffold_ca_python.core.module_locator import find_module_targets
from scaffold_ca_python.core.name_utils import to_snake_case
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import remove_test_function, sync_wiring_marker
from scaffold_ca_python.factory import ModuleFactory
from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class DeleteModuleFactory(ModuleFactory):
    """Factory for module deletion."""

    def build(self, builder: ModuleBuilder) -> None:
        """Perform deletion for a module (invoked only after ``dm --confirm``).

        Finds and deletes modules across:
        - domain/model/<snake>/ (package) or domain/model/<snake>.py (legacy)
        - domain/usecase/<base>_usecase.py or domain/usecase/<snake>.py (legacy)
        - infrastructure/driven_adapters/<snake>/
        - infrastructure/entry_points/<snake>/
        - infrastructure/helpers/<snake>/
        """
        project_root = builder.project_root
        src_pkg_root = builder.project_ctx.src_pkg_root

        assert builder.module_ctx is not None
        snake_name = to_snake_case(builder.module_ctx.name)

        candidates = find_module_targets(project_root, src_pkg_root, snake_name)

        tests_root = resolve_tests_root(project_root)
        factory_path = src_pkg_root / "application" / "config" / "usecases" / f"{snake_name}_usecase.py"
        factory_test_path = tests_root / "application" / "config" / "usecases" / f"test_{snake_name}_usecase.py"
        wiring_test_path = tests_root / "application" / "config" / "test_wiring.py"
        wiring_fn_name = f"test_container_resolves_{snake_name}_usecase"

        for src_path, test_path in candidates:
            self._delete_path(src_path)
            if test_path:
                self._delete_path(test_path)
        if factory_path.exists():
            factory_path.unlink()
        if factory_test_path.exists():
            factory_test_path.unlink()
        if wiring_test_path.exists():
            source = wiring_test_path.read_text(encoding="utf-8")
            for fn_name in (wiring_fn_name, f"test_container_resolves_{snake_name}"):
                source = remove_test_function(source, fn_name) or source
            wiring_test_path.write_text(source, encoding="utf-8")
        sync_wiring_marker(src_pkg_root, tests_root)
        _CONFTEST_FIXTURE_NAMES = {
            DrivenAdapterRestConsumer.fixed_name: "rest_consumer_env",
            "sqlalchemy": "sqlalchemy_env",
        }
        if snake_name in _CONFTEST_FIXTURE_NAMES:
            self._remove_conftest_fixture(tests_root, _CONFTEST_FIXTURE_NAMES[snake_name])

    @staticmethod
    def _delete_path(path: Path) -> None:
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

    @staticmethod
    def _remove_conftest_fixture(tests_root: Path, fixture_name: str) -> None:
        """Remove a named autouse fixture from conftest.py if present."""
        import re

        conftest_path = tests_root / "conftest.py"
        if not conftest_path.exists():
            return
        source = conftest_path.read_text(encoding="utf-8")
        if fixture_name not in source:
            return
        pattern = rf"\n@pytest\.fixture\(autouse=True\)\ndef {re.escape(fixture_name)}\(.*?\) -> None:.*?(?=\n\n|\Z)"
        cleaned = re.sub(pattern, "", source, flags=re.DOTALL)
        if cleaned != source:
            conftest_path.write_text(cleaned, encoding="utf-8")
        final = conftest_path.read_text(encoding="utf-8")
        if "import pytest" in final and "@pytest.fixture" not in final:
            orphan_header = re.sub(
                (
                    r'^"""Test fixtures for the generated project\."""\n\n'
                    r"from __future__ import annotations\n\nimport pytest\n"
                ),
                "",
                final,
                count=1,
            )
            if orphan_header != final:
                orphan_header = orphan_header.lstrip("\n")
                if orphan_header.strip():
                    conftest_path.write_text(orphan_header, encoding="utf-8")
                else:
                    conftest_path.unlink(missing_ok=True)
