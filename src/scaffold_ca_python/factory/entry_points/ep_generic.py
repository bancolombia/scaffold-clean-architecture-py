from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointGeneric(EntryPointFactory):
    """Factory for Generic entry-point type."""

    description: ClassVar[str] = "Custom entry point (minimal scaffold)"
    subdir: ClassVar[str] = "generic"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset()
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = ()

    def build(self, builder: ModuleBuilder) -> None:
        """Queue Generic entry-point files and overwrite main.py."""
        src_dir = type(self).entry_points_src(builder)
        test_dir = type(self).entry_points_tests(builder)
        main_py = type(self).pkg_file(builder, "main.py")
        generic_app_py = type(self).pkg_file(builder, "application", "generic_app.py")

        base = "entry_point/generic"

        ctx_dict = dict(builder.base_context())

        def tpl(f: str) -> str:
            return f"{base}/{f}"

        builder.add_rendered(generic_app_py, tpl("generic_app.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "__init__.py", tpl("__init__.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "entry_point.py", tpl("handler.py.jinja2"), ctx_dict)
        builder.add_rendered(test_dir / "test_entry_point.py", tpl("test_handler.py.jinja2"), ctx_dict)
        builder.add_rendered(main_py, tpl("entrypoint_main.py.jinja2"), ctx_dict, overwrite=True)
