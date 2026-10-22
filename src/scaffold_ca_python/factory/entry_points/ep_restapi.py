"""EntryPointRestApi factory implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointRestApi(EntryPointFactory):
    """Factory for REST API entry-point type."""

    subdir: ClassVar[str] = "api/v1"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset(
        {EntryPointFlag.SWAGGER, EntryPointFlag.ENABLE_MCP_CLIENT, EntryPointFlag.ENABLE_KAFKA}
    )
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = (
        EntryPointConflict(label="mcp_server", subdir="mcp_server"),
        EntryPointConflict(label="agent", subdir="agent"),
    )

    def result_notes(self, project_root: Path, pkg: str, type_key: str, *, dry_run: bool) -> list[str]:  # noqa: ARG002
        notes: list[str] = []
        main_py = project_root / "src" / pkg / "main.py"
        if dry_run:
            if main_py.exists():
                notes.append(f"[dim]Would delete: src/{pkg}/main.py[/dim]")
            notes.append(f'[dim]Would update [project.scripts]: {pkg} = "{pkg}.server:start_server"[/dim]')
        else:
            if main_py.exists():
                notes.append(f"[green]✓[/green] Deleted src/{pkg}/main.py")
            notes.append(f'[green]✓[/green] Updated [project.scripts]: {pkg} = "{pkg}.server:start_server"')
        return notes

    def build(self, builder: ModuleBuilder) -> None:
        """Build REST API entry-point files and dependencies.

        Queues files:
        - src/application/app.py (application factory)
        - src/infrastructure/entry_points/api/v1/__init__.py
        - src/infrastructure/entry_points/api/v1/rest_controller.py
        - src/infrastructure/entry_points/api/v1/exception_handler.py
        - src/server.py (entrypoint)
        - tests/application/test_app.py
        - tests/infrastructure/entry_points/api/v1/test_rest_controller.py
        - tests/infrastructure/entry_points/api/v1/test_server.py
        - tests/infrastructure/entry_points/api/v1/test_exception_handler.py

        Deletes:
        - src/main.py

        Injects:
        - fastapi[standard]~=0.141.1
        - uvicorn[standard]~=0.53.0
        - dependency-injector~=4.49.1
        - pydantic-settings~=2.15.0
        """
        project_root = builder.project_root
        pkg = builder.project_ctx.python_package

        # Setup directory paths
        src_dir = project_root / "src" / pkg / "infrastructure" / "entry_points" / "api" / "v1"
        test_dir = resolve_tests_root(project_root) / "infrastructure" / "entry_points" / "api" / "v1"
        app_py_path = project_root / "src" / pkg / "application" / "app.py"
        server_path = project_root / "src" / pkg / "server.py"
        test_app_path = resolve_tests_root(project_root) / "application" / "test_app.py"
        main_py = project_root / "src" / pkg / "main.py"

        # Template base path for entry_point/restapi
        base = "entry_point/restapi"

        # Build context dict from module context
        ctx_dict = (
            {
                **builder.module_ctx.model_dump(),
            }
            if builder.module_ctx
            else {}
        )

        # Add source files
        def tpl(f: str) -> str:
            return f"{base}/{f}"

        builder.add_file(
            app_py_path,
            builder.render(f"{base}/app.py.jinja2", ctx_dict),
            template_name=tpl("app.py.jinja2"),
        )
        builder.add_file(
            src_dir / "__init__.py",
            builder.render(f"{base}/__init__.py.jinja2", ctx_dict),
            template_name=tpl("__init__.py.jinja2"),
        )
        builder.add_file(
            src_dir / "rest_controller.py",
            builder.render(f"{base}/rest_controller.py.jinja2", ctx_dict),
            template_name=tpl("rest_controller.py.jinja2"),
        )
        builder.add_file(
            src_dir / "exception_handler.py",
            builder.render(f"{base}/exception_handler.py.jinja2", ctx_dict),
            template_name=tpl("exception_handler.py.jinja2"),
        )
        builder.add_file(
            server_path,
            builder.render(f"{base}/server.py.jinja2", ctx_dict),
            template_name=tpl("server.py.jinja2"),
        )

        # Add test files
        builder.add_file(
            test_dir / "test_rest_controller.py",
            builder.render(f"{base}/test_rest_controller.py.jinja2", ctx_dict),
            template_name=tpl("test_rest_controller.py.jinja2"),
            is_test=True,
        )
        builder.add_file(
            test_dir / "test_server.py",
            builder.render(f"{base}/test_server.py.jinja2", ctx_dict),
            template_name=tpl("test_server.py.jinja2"),
            is_test=True,
        )
        builder.add_file(
            test_dir / "test_exception_handler.py",
            builder.render(f"{base}/test_exception_handler.py.jinja2", ctx_dict),
            template_name=tpl("test_exception_handler.py.jinja2"),
            is_test=True,
        )
        builder.add_file(
            test_app_path,
            builder.render(f"{base}/test_app.py.jinja2", ctx_dict),
            template_name=tpl("test_app.py.jinja2"),
            is_test=True,
        )

        # Delete main.py
        builder.delete_file(main_py)

        # Add dependencies
        deps = [
            "fastapi[standard]~=0.141.1",
            "uvicorn[standard]~=0.53.0",
            "dependency-injector~=4.49.1",
            "pydantic-settings~=2.15.0",
        ]
        for dep in deps:
            builder.add_dependency(dep)

        builder.set_project_script()
