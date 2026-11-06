from __future__ import annotations

from typing import TYPE_CHECKING

from scaffold_ca_python.core.name_utils import to_snake_case
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class HelperFactory(ModuleFactory):
    """Factory for helper utility generation."""

    def build(self, builder: ModuleBuilder) -> None:
        """Queue helper module sources and tests under infrastructure/helpers."""
        pkg_root = builder.project_ctx.src_pkg_root

        assert builder.module_ctx is not None
        snake_name = to_snake_case(builder.module_ctx.name)

        src_dir = pkg_root / "infrastructure" / "helpers" / snake_name
        test_dir = resolve_tests_root(builder.project_root) / "infrastructure" / "helpers" / snake_name
        base = "helper"
        ctx_dict = dict(builder.base_context())

        builder.add_rendered(src_dir / "__init__.py", f"{base}/__init__.py.jinja2", ctx_dict)
        builder.add_rendered(src_dir / f"{snake_name}.py", f"{base}/helper.py.jinja2", ctx_dict)
        builder.add_rendered(test_dir / f"test_{snake_name}.py", f"{base}/test_helper.py.jinja2", ctx_dict)
