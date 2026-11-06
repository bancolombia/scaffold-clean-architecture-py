from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.factory.dependencies import A2A_SDK
from scaffold_ca_python.factory.entry_points.base import (
    EntryPointConflict,
    EntryPointFactory,
    EntryPointFlag,
)

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder


class EntryPointAgent(EntryPointFactory):
    """Factory for Agent entry-point type."""

    description: ClassVar[str] = "Async agent with optional Kafka consumer and MCP client"
    subdir: ClassVar[str] = "agent"
    supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset(
        {EntryPointFlag.ENABLE_MCP_CLIENT, EntryPointFlag.ENABLE_KAFKA}
    )
    conflicts: ClassVar[tuple[EntryPointConflict, ...]] = (EntryPointConflict(type_key="restapi"),)

    def build(self, builder: ModuleBuilder) -> None:
        """Queue Agent entry-point files, overwrite main.py, and inject runtime deps."""
        src_dir = type(self).entry_points_src(builder)
        test_dir = type(self).entry_points_tests(builder)
        main_py = type(self).pkg_file(builder, "main.py")
        agent_app_py = type(self).pkg_file(builder, "application", "agent_app.py")

        base = "entry_point/agent"
        ctx_dict = dict(builder.base_context())

        if builder.get_param("enable_kafka"):
            ctx_dict["enable_kafka"] = True
        if builder.get_param("enable_mcp_client"):
            ctx_dict["enable_mcp_client"] = True

        def tpl(f: str) -> str:
            return f"{base}/{f}"

        builder.add_rendered(agent_app_py, tpl("agent_app.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "__init__.py", tpl("__init__.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "agent.py", tpl("agent.py.jinja2"), ctx_dict)
        builder.add_rendered(src_dir / "card.py", tpl("card.py.jinja2"), ctx_dict)
        builder.add_rendered(test_dir / "test_agent.py", tpl("test_agent.py.jinja2"), ctx_dict)
        builder.add_rendered(main_py, tpl("entrypoint_main.py.jinja2"), ctx_dict, overwrite=True)

        builder.add_dependency(A2A_SDK)
