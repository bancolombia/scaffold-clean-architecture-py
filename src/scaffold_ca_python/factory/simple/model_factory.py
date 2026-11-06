from __future__ import annotations

from typing import TYPE_CHECKING

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class ModelFactory(ModuleFactory):
    """Factory for domain model generation."""

    def build(self, builder: ModuleBuilder) -> None:
        """Queue domain model, gateway port, and test files."""
        pkg_root = builder.project_ctx.src_pkg_root
        assert builder.module_ctx is not None
        module_name = builder.module_ctx.module_name

        src_dir = pkg_root / "domain" / "model" / module_name
        gateways_dir = src_dir / "gateways"
        test_dir = resolve_tests_root(builder.project_root) / "domain" / "model" / module_name
        test_gateways_dir = test_dir / "gateways"

        base = "model"

        ctx_dict = dict(builder.base_context())

        files = [
            (src_dir / "__init__.py", "__init__.py.jinja2"),
            (src_dir / f"{module_name}.py", "model.py.jinja2"),
            (gateways_dir / "__init__.py", "gateways_init.py.jinja2"),
            (gateways_dir / f"{module_name}_repository.py", "gateway.py.jinja2"),
            (test_dir / f"test_{module_name}.py", "test_model.py.jinja2"),
            (test_gateways_dir / f"test_{module_name}_repository.py", "test_gateway.py.jinja2"),
        ]
        for path, template in files:
            template_name = f"{base}/{template}"
            builder.add_rendered(path, template_name, ctx_dict)
