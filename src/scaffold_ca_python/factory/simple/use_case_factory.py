"""UseCaseFactory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from scaffold_ca_python.core.name_utils import to_pascal_case, to_snake_case
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import find_existing_test_function_names
from scaffold_ca_python.factory import ModuleFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


def _gateway_context(gateway_name: str, model_module: str) -> dict[str, str]:
    """Build the per-gateway dict used in Jinja2 templates."""
    return {
        "name": gateway_name,
        "class_name": to_pascal_case(gateway_name),
        "model_module": model_module,
    }


class UseCaseFactory(ModuleFactory):
    """Factory for domain use case generation."""

    def build(self, builder: ModuleBuilder) -> None:
        """Build domain use case files.

        Queues files:
        - src/domain/usecase/{snake_name}_usecase.py
        - tests/domain/usecase/test_{snake_name}_usecase.py
        - src/application/config/usecases/{snake_name}_usecase.py  (only when gateways provided)
        """
        project_root = builder.project_root
        pkg = builder.project_ctx.python_package

        usecase_name = builder.module_ctx.name if builder.module_ctx else "UseCase"
        snake_name = to_snake_case(usecase_name)

        src_dir = project_root / "src" / pkg / "domain" / "usecase"
        test_dir = resolve_tests_root(project_root) / "domain" / "usecase"
        config_dir = project_root / "src" / pkg / "application" / "config" / "usecases"

        base = "use_case"

        ctx_dict: dict[str, Any] = {}
        if builder.module_ctx:
            ctx_dict.update(builder.module_ctx.model_dump())

        # gateways is a list[dict] set by generate_use_case when --uses is given
        raw_gateways = builder.get_param("gateways", default=[])
        gateways: list[dict[str, str]] = sorted(
            raw_gateways if isinstance(raw_gateways, list) else [],
            key=lambda g: g.get("name", ""),
        )
        ctx_dict["gateways"] = gateways

        builder.add_file(
            src_dir / f"{snake_name}_usecase.py",
            builder.render(f"{base}/use_case.py.jinja2", ctx_dict),
            template_name=f"{base}/use_case.py.jinja2",
        )

        builder.add_file(
            test_dir / f"test_{snake_name}_usecase.py",
            builder.render(f"{base}/test_use_case.py.jinja2", ctx_dict),
            template_name=f"{base}/test_use_case.py.jinja2",
            is_test=True,
        )

        if gateways:
            config_test_dir = resolve_tests_root(project_root) / "application" / "config" / "usecases"
            wiring_test_path = resolve_tests_root(project_root) / "application" / "config" / "test_wiring.py"
            fn_name = f"test_container_resolves_{snake_name}_usecase"
            builder.add_file(
                config_dir / f"{snake_name}_usecase.py",
                builder.render(f"{base}/use_case_factory.py.jinja2", ctx_dict),
                template_name=f"{base}/use_case_factory.py.jinja2",
            )
            builder.add_file(
                config_test_dir / f"test_{snake_name}_usecase.py",
                builder.render(f"{base}/test_use_case_factory.py.jinja2", ctx_dict),
                template_name=f"{base}/test_use_case_factory.py.jinja2",
                is_test=True,
            )
            existing_src = wiring_test_path.read_text(encoding="utf-8") if wiring_test_path.exists() else ""
            if fn_name not in find_existing_test_function_names(existing_src):
                builder.append_to_file(
                    wiring_test_path,
                    builder.render(f"{base}/wiring_test_stub.py.jinja2", ctx_dict),
                )
