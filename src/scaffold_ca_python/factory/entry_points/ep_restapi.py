from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from rich.markup import escape

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.dependencies import RESTAPI_RUNTIME
from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointRestApi(EntryPointFactory):
    """Factory for REST API entry-point type."""

    description: ClassVar[str] = "FastAPI REST adapter with OpenAPI support"
    subdir: ClassVar[str] = "api/v1"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset({EntryPointFlag.SWAGGER})
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = (
        EntryPointConflict(type_key="mcp"),
        EntryPointConflict(type_key="agent"),
    )

    def result_notes(self, src_pkg_root: Path, pkg: str, type_key: str, *, dry_run: bool) -> list[str]:
        notes: list[str] = []
        main_py = src_pkg_root / "main.py"
        if dry_run:
            if main_py.exists():
                notes.append(f"[dim]Would delete: src/{pkg}/main.py[/dim]")
            notes.append(f'[dim]Would update {escape("[project.scripts]")}: {pkg} = "{pkg}.server:start_server"[/dim]')
        else:
            if main_py.exists():
                notes.append(f"[green]✓[/green] Deleted src/{pkg}/main.py")
            notes.append(f'[green]✓[/green] Updated {escape("[project.scripts]")}: {pkg} = "{pkg}.server:start_server"')
        return notes

    def build(self, builder: ModuleBuilder) -> None:
        """Queue REST API entry-point files, remove main.py, and inject runtime deps."""
        src_dir = type(self).entry_points_src(builder)
        test_dir = type(self).entry_points_tests(builder)
        app_py_path = type(self).pkg_file(builder, "application", "app.py")
        server_path = type(self).pkg_file(builder, "server.py")
        test_app_path = resolve_tests_root(builder.project_root) / "application" / "test_app.py"
        main_py = type(self).pkg_file(builder, "main.py")

        base = "entry_point/restapi"
        ctx_dict = dict(builder.base_context())
        ctx_dict["routes"] = builder.get_param("routes", default=[])

        def tpl(f: str) -> str:
            return f"{base}/{f}"

        builder.add_rendered(app_py_path, tpl("app.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "__init__.py", tpl("__init__.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "rest_controller.py", tpl("rest_controller.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "exception_handler.py", tpl("exception_handler.py.jinja2"), ctx_dict)
        builder.add_rendered(server_path, tpl("server.py.jinja2"), ctx_dict)

        builder.add_rendered(test_dir / "test_rest_controller.py", tpl("test_rest_controller.py.jinja2"), ctx_dict)
        builder.add_rendered(test_dir / "test_server.py", tpl("test_server.py.jinja2"), ctx_dict)
        builder.add_rendered(
            test_dir / "test_exception_handler.py",
            tpl("test_exception_handler.py.jinja2"),
            ctx_dict,
        )
        builder.add_rendered(test_app_path, tpl("test_app.py.jinja2"), ctx_dict)

        # Delete main.py
        builder.delete_file(main_py)

        for dep in RESTAPI_RUNTIME:
            builder.add_dependency(dep)

        builder.set_project_script()
