from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.core.name_utils import to_pascal_case, to_snake_case
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.factory.driven_adapters.base import FileSpec as _FileSpec


class DrivenAdapterGeneric(DrivenAdapterFactory):
    """Factory for Generic driven-adapter type."""

    description: ClassVar[str] = "Custom adapter (--name required)"
    template_pkg: ClassVar[str] = "driven_adapter/generic"
    src_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("__init__.py", "__init__.py.jinja2"),
        ("adapter.py", "adapter.py.jinja2"),
    )

    def module_dir(self, builder: ModuleBuilder) -> str:
        assert builder.module_ctx is not None
        return to_snake_case(builder.module_ctx.name)

    def _base_name(self, builder: ModuleBuilder) -> str:
        return self.module_dir(builder).removesuffix("_adapter")

    def adapter_context(self, builder: ModuleBuilder) -> dict[str, object]:
        ctx = super().adapter_context(builder)
        ctx["class_name"] = to_pascal_case(self._base_name(builder))
        return ctx

    def test_file_specs(self, builder: ModuleBuilder) -> tuple[_FileSpec, ...]:
        base_name = self._base_name(builder)
        return ((f"test_{base_name}_adapter.py", "test_adapter.py.jinja2"),)
