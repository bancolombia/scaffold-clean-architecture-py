"""ModelFactory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class ModelFactory(ModuleFactory):
    """Factory for domain model generation."""

    def build(self, builder: ModuleBuilder) -> None:
        """Build domain model package files.

        Queues files:
        - src/domain/model/{module_name}/__init__.py
        - src/domain/model/{module_name}/{module_name}.py
        - src/domain/model/{module_name}/gateways/__init__.py
        - src/domain/model/{module_name}/gateways/{module_name}_repository.py
        - tests/domain/model/{module_name}/test_{module_name}.py
        - tests/domain/model/{module_name}/gateways/test_{module_name}_repository.py

        No dependencies injected (pydantic is already a project dependency).
        """
        project_root = builder.project_root
        pkg = builder.project_ctx.python_package

        module_name = builder.module_ctx.module_name if builder.module_ctx else "model"

        src_dir = project_root / "src" / pkg / "domain" / "model" / module_name
        gateways_dir = src_dir / "gateways"
        test_dir = resolve_tests_root(project_root) / "domain" / "model" / module_name
        test_gateways_dir = test_dir / "gateways"

        base = "model"

        ctx_dict = {}
        if builder.module_ctx:
            ctx_dict.update(builder.module_ctx.model_dump())

        # (target path, template file name, is_test)
        files = [
            (src_dir / "__init__.py", "__init__.py.jinja2", False),
            (src_dir / f"{module_name}.py", "model.py.jinja2", False),
            (gateways_dir / "__init__.py", "gateways_init.py.jinja2", False),
            (gateways_dir / f"{module_name}_repository.py", "gateway.py.jinja2", False),
            (test_dir / f"test_{module_name}.py", "test_model.py.jinja2", True),
            (test_gateways_dir / f"test_{module_name}_repository.py", "test_gateway.py.jinja2", True),
        ]
        for path, template, is_test in files:
            template_name = f"{base}/{template}"
            builder.add_file(
                path,
                builder.render(template_name, ctx_dict),
                template_name=template_name,
                is_test=is_test,
            )
