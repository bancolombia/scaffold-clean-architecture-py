"""Base class for driven-adapter factories."""

from __future__ import annotations

from abc import ABC
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.wiring_utils import append_test_once

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

# (destination filename under module dir, template filename under template_pkg)
FileSpec = tuple[str, str]


class DrivenAdapterFactory(ABC):
    """Abstract base for driven-adapter factories.

    Subclasses declare ``template_pkg``, ``src_files``, optional ``test_files``,
    and dependencies; override hooks when paths or context are dynamic.
    """

    description: ClassVar[str] = ""
    fixed_name: ClassVar[str | None] = None
    template_pkg: ClassVar[str]
    src_files: ClassVar[tuple[FileSpec, ...]] = ()
    test_files: ClassVar[tuple[FileSpec, ...]] = ()
    runtime_dependencies: ClassVar[tuple[str, ...]] = ()
    test_group_dependencies: ClassVar[tuple[str, ...]] = ()

    def module_name(self, name: str | None) -> str | None:
        """Return the module directory name: fixed_name if set, else the user-supplied name."""
        return self.fixed_name or name

    def module_dir(self, builder: ModuleBuilder) -> str:
        """Directory name under infrastructure/driven_adapters/."""
        fixed = type(self).fixed_name
        if fixed is not None:
            return fixed
        msg = f"{type(self).__name__} must override module_dir() when fixed_name is unset"
        raise NotImplementedError(msg)

    def adapter_context(self, builder: ModuleBuilder) -> dict[str, Any]:
        ctx = dict(builder.base_context())
        ctx["gateway"] = builder.get_param("gateway", default=None)
        return ctx

    def test_file_specs(self, builder: ModuleBuilder) -> tuple[FileSpec, ...]:
        return type(self).test_files

    @classmethod
    def adapter_src_dir(cls, builder: ModuleBuilder, module_dir: str) -> Path:
        return builder.project_ctx.src_pkg_root / "infrastructure" / "driven_adapters" / module_dir

    @classmethod
    def adapter_test_dir(cls, builder: ModuleBuilder, module_dir: str) -> Path:
        return resolve_tests_root(builder.project_root) / "infrastructure" / "driven_adapters" / module_dir

    def build(self, builder: ModuleBuilder) -> None:
        """Template method: render declared files, wiring test stub, and dependencies."""
        module = self.module_dir(builder)
        src_dir = type(self).adapter_src_dir(builder, module)
        test_dir = type(self).adapter_test_dir(builder, module)
        ctx = self.adapter_context(builder)
        tpl_base = type(self).template_pkg

        for dest, tpl in type(self).src_files:
            builder.add_rendered(src_dir / dest, f"{tpl_base}/{tpl}", ctx)

        self.append_wiring_test(builder, ctx)

        for dest, tpl in self.test_file_specs(builder):
            builder.add_rendered(test_dir / dest, f"{tpl_base}/{tpl}", ctx)

        for dep in type(self).runtime_dependencies:
            builder.add_dependency(dep)
        for dep in type(self).test_group_dependencies:
            builder.add_dependency(dep, group="test")

        self.build_extra(builder, ctx)

    def build_extra(self, builder: ModuleBuilder, ctx: dict[str, Any]) -> None:
        """Hook for type-specific steps after the standard file queue."""
        return

    @staticmethod
    def append_wiring_test(builder: ModuleBuilder, ctx_dict: dict[str, Any]) -> None:
        """Append ``test_container_resolves_<module>`` to test_wiring.py when a gateway is bound."""
        if not ctx_dict.get("gateway"):
            return
        wiring_test_path = resolve_tests_root(builder.project_root) / "application" / "config" / "test_wiring.py"
        fn_name = f"test_container_resolves_{ctx_dict['module_name']}"
        append_test_once(
            builder,
            wiring_test_path,
            fn_name,
            "driven_adapter/wiring_test_stub.py.jinja2",
            ctx_dict,
        )
