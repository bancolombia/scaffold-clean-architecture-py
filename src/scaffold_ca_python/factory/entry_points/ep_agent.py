from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, override

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.dependencies import A2A_RUNTIME
from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
    server_entry_notes,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

_PACKAGE_FILES = ("__init__", "agent_settings", "a2a_config", "agent_executor", "agent_card", "routes")
_TEST_FILES = ("test_agent_executor", "test_agent_card", "test_routes")


class EntryPointAgent(EntryPointFactory):
    """Factory for the A2A agent entry-point type."""

    description: ClassVar[str] = "A2A agent server (a2a-sdk, Starlette)"
    subdir: ClassVar[str] = "a2a_server"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset()
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = (
        EntryPointConflict(type_key="restapi"),
        EntryPointConflict(type_key="mcp"),
    )

    @override
    def result_notes(self, src_pkg_root: Path, pkg: str, type_key: str, *, dry_run: bool) -> list[str]:
        return server_entry_notes(src_pkg_root, pkg, "main", dry_run=dry_run)

    def build(self, builder: ModuleBuilder) -> None:
        """Queue the A2A server files, replace main.py with server.py, and inject runtime deps."""
        src_dir = type(self).entry_points_src(builder)
        test_dir = type(self).entry_points_tests(builder)
        base = "entry_point/agent"
        ctx_dict = dict(builder.base_context())

        for name in _PACKAGE_FILES:
            builder.add_rendered(src_dir / f"{name}.py", f"{base}/{name}.py.jinja2", ctx_dict)
        for name in _TEST_FILES:
            builder.add_rendered(test_dir / f"{name}.py", f"{base}/{name}.py.jinja2", ctx_dict)

        server_py = type(self).pkg_file(builder, "server.py")
        builder.add_rendered(server_py, f"{base}/server.py.jinja2", ctx_dict, overwrite=True)
        builder.delete_file(type(self).pkg_file(builder, "main.py"))

        builder.insert_after(
            type(self).pkg_file(builder, "application", "config", "config.py"),
            anchor="LOG_LEVEL",
            content='    HOST: str = "0.0.0.0"\n    PORT: int = 8000',
        )

        builder.add_rendered(type(self).pkg_file(builder, "application", "app.py"), f"{base}/app.py.jinja2", ctx_dict)
        test_app = resolve_tests_root(builder.project_root) / "application" / "test_app.py"
        builder.add_rendered(test_app, f"{base}/test_app.py.jinja2", ctx_dict)

        for dep in A2A_RUNTIME:
            builder.add_dependency(dep)

        builder.set_project_script("main")
