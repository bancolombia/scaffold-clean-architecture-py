from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from rich.markup import escape

from scaffold_ca_python.factory.dependencies import MCP_RUNTIME
from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointMcp(EntryPointFactory):
    """Factory for MCP entry-point type."""

    subdir: ClassVar[str] = "mcp_server"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset({EntryPointFlag.MCP_PRIMITIVES})
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = (EntryPointConflict(type_key="restapi"),)

    def result_notes(
        self,
        src_pkg_root: Path,
        pkg: str,
        type_key: str,
        *,
        dry_run: bool,
    ) -> list[str]:
        notes: list[str] = []
        main_py = src_pkg_root / "main.py"
        if dry_run:
            if main_py.exists():
                notes.append(f"[dim]Would delete: src/{pkg}/main.py[/dim]")
            notes.append(f'[dim]Would update {escape("[project.scripts]")}: {pkg} = "{pkg}.server:start_server"[/dim]')
        else:
            notes.append(f"[green]✓[/green] Deleted src/{pkg}/main.py")
            notes.append(f'[green]✓[/green] Updated {escape("[project.scripts]")}: {pkg} = "{pkg}.server:start_server"')
        return notes

    def build(self, builder: ModuleBuilder) -> None:
        """Queue MCP entry-point files, optional resources/prompts, and runtime deps."""
        with_resources: bool = bool(builder.get_param("with_resources", False))
        with_prompts: bool = bool(builder.get_param("with_prompts", False))

        src_dir = type(self).entry_points_src(builder)
        test_dir = type(self).entry_points_tests(builder)

        base = "entry_point/mcp"

        ctx_dict = dict(builder.base_context())

        builder.add_rendered(src_dir / "__init__.py", f"{base}/__init__.py.jinja2", ctx_dict)
        builder.add_rendered(src_dir / "tools.py", f"{base}/tools.py.jinja2", ctx_dict)
        builder.add_rendered(src_dir / "routes.py", f"{base}/routes.py.jinja2", ctx_dict)
        builder.add_rendered(test_dir / "test_tools.py", f"{base}/test_tools.py.jinja2", ctx_dict)
        builder.add_rendered(test_dir / "test_routes.py", f"{base}/test_routes.py.jinja2", ctx_dict)

        if with_resources:
            builder.add_rendered(src_dir / "resources.py", f"{base}/resources.py.jinja2", ctx_dict)
            builder.add_rendered(test_dir / "test_resources.py", f"{base}/test_resources.py.jinja2", ctx_dict)

        if with_prompts:
            builder.add_rendered(src_dir / "prompts.py", f"{base}/prompts.py.jinja2", ctx_dict)
            builder.add_rendered(test_dir / "test_prompts.py", f"{base}/test_prompts.py.jinja2", ctx_dict)

        # server.py at package root — replaces main.py
        server_path = type(self).pkg_file(builder, "server.py")
        main_py = type(self).pkg_file(builder, "main.py")
        builder.add_rendered(server_path, f"{base}/server.py.jinja2", ctx_dict, overwrite=True)
        builder.delete_file(main_py)

        # config.py — add HOST / PORT for uvicorn via insert_after
        config_py_path = type(self).pkg_file(builder, "application", "config", "config.py")
        builder.insert_after(
            config_py_path,
            anchor="LOG_LEVEL",
            content='    HOST: str = "0.0.0.0"\n    PORT: int = 8000',
        )

        # app.py composition root — no overwrite guard
        app_py_path = type(self).pkg_file(builder, "application", "app.py")
        app_ctx: dict[str, object] = {**ctx_dict, "with_resources": with_resources, "with_prompts": with_prompts}
        builder.add_rendered(app_py_path, f"{base}/app.py.jinja2", app_ctx)
        builder.add_rendered(test_dir / "test_app.py", f"{base}/test_app.py.jinja2", app_ctx)

        for dep in MCP_RUNTIME:
            builder.add_dependency(dep)

        builder.set_project_script("main")
