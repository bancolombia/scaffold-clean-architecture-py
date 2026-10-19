"""generate_entry_point: scaffold an entry-point adapter and test stub (T055)."""

from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.markup import escape
from rich.syntax import Syntax
from rich.tree import Tree

from scaffold_ca_python.core import mcp_tool_spec
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.name_utils import ScaffoldError, to_snake_case
from scaffold_ca_python.core.project_detector import find_project_root, resolve_tests_root
from scaffold_ca_python.factory import ModuleFactory
from scaffold_ca_python.factory.entry_points.ep_agent import EntryPointAgent
from scaffold_ca_python.factory.entry_points.ep_generic import EntryPointGeneric
from scaffold_ca_python.factory.entry_points.ep_mcp import EntryPointMcp
from scaffold_ca_python.factory.entry_points.ep_restapi import EntryPointRestApi
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer

console = Console()

_REGISTRY: dict[str, type[ModuleFactory]] = {
    "restapi": EntryPointRestApi,
    "agent": EntryPointAgent,
    "mcp": EntryPointMcp,
    "generic": EntryPointGeneric,
}

_TYPE_HELP = "Entry-point type: restapi, agent, mcp, generic."
_SWAGGER_HELP = "Path to OpenAPI YAML/JSON (restapi only)."
_KAFKA_HELP = "Add async Kafka consumer stub (agent type only)."
_MCP_CLIENT_HELP = "Add MCP tool-call client stub (agent type only)."
_GEP_HELP = "Scaffold an entry-point adapter and test stub. Alias 'gep'."
_GEP_EPILOG = (
    "Types:\n\n"
    "  * restapi    FastAPI REST API entry point\n\n"
    "  * agent      A2A agent entry point\n\n"
    "  * mcp        MCP server entry point\n\n"
    "  * generic    Plain entry point\n\n"
    " ==================================================\n\n"
    "Examples:\n\n"
    "  * scaffold gep --type restapi\n\n"
    "  * scaffold gep --type agent --enable-kafka\n\n"
    "  * scaffold gep --type mcp\n\n"
    "  * scaffold gep --type mcp --add-tool --name create_file --param path:str --returns str\n\n"
    "  * scaffold generate-entry-point --type generic\n"
)


def _load_project_context(project_root: Path) -> ProjectContext:
    """Load project context from pyproject.toml."""
    pyproject_path = project_root / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    project_name = to_snake_case(data.get("project", {}).get("name", "project"))
    return ProjectContext(name=project_name)


def _add_tool_impl(
    type_: str,
    swagger: str | None,
    enable_kafka: bool,
    enable_mcp_client: bool,
    with_resources: bool,
    with_prompts: bool,
    name: str | None,
    param: list[str] | None,
    returns: str,
    description: str | None,
    dry_run: bool,
) -> None:
    """Add a tool to an existing MCP entry point (T018-T021, T027-T030a).

    Implements User Story 1 and 2: appends a tool stub to tools.py and a registration
    test to test_tools.py in an existing MCP project, with comprehensive guard rails.
    """
    # T028: Flag/type incompatibility guards (FR-011, FR-012) - before project access
    # Check creation-only flags
    creation_flags = []
    if swagger is not None:
        creation_flags.append("--swagger")
    if enable_kafka:
        creation_flags.append("--enable-kafka")
    if enable_mcp_client:
        creation_flags.append("--enable-mcp-client")
    if with_resources:
        creation_flags.append("--with-resources")
    if with_prompts:
        creation_flags.append("--with-prompts")

    if creation_flags:
        flag = creation_flags[0]
        console.print(f"[red]Error:[/red] --add-tool is incompatible with {flag}.")
        raise typer.Exit(code=1)

    # Check type compatibility (FR-012) - handled by T016(a) for --type omitted
    # Here we check non-mcp types
    if type_ != "mcp":
        console.print("[red]Error:[/red] --add-tool is only valid with --type mcp.")
        raise typer.Exit(code=1)

    # T018: Format-only validation (no filesystem access yet)
    if name is None:
        console.print("[red]Error:[/red] --name is required with --add-tool.")
        raise typer.Exit(code=1)

    try:
        tool_spec = mcp_tool_spec.build_tool_spec(name, param, returns, description)
    except (ValueError, ScaffoldError) as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    # T019: Resolve project root and check entry point exists
    try:
        project_root = find_project_root()
    except ScaffoldError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(code=1) from None

    project_ctx = _load_project_context(project_root)

    tools_py_path = (
        project_root
        / "src"
        / project_ctx.python_package
        / "infrastructure"
        / "entry_points"
        / "mcp_server"
        / "tools.py"
    )
    test_tools_py_path = (
        resolve_tests_root(project_root) / "infrastructure" / "entry_points" / "mcp_server" / "test_tools.py"
    )

    if not tools_py_path.exists():
        console.print(
            "[red]Error:[/red] No MCP entry point found at infrastructure/entry_points/mcp_server/.\n"
            "[dim]Hint:[/dim] Run [cyan]scaffold gep --type mcp[/cyan] first to create one."
        )
        raise typer.Exit(code=1)

    # T020: Read files and check structure
    try:
        original_tools_py = tools_py_path.read_text(encoding="utf-8")
    except OSError as e:
        console.print(f"[red]Error:[/red] Cannot read {tools_py_path}: {e}")
        raise typer.Exit(code=1) from None

    try:
        original_test_tools_py = test_tools_py_path.read_text(encoding="utf-8")
    except OSError:
        console.print(
            "[red]Error:[/red] tests/infrastructure/entry_points/mcp_server/test_tools.py is missing or "
            "does not have\n"
            "the structure --add-tool needs to append a registration test.\n"
            "[dim]Hint:[/dim] Restore test_tools.py, or regenerate the entry point with "
            "[cyan]scaffold gep --type mcp[/cyan]."
        )
        raise typer.Exit(code=1)

    # Check bind_tools is last top-level statement
    if not mcp_tool_spec.has_bind_tools_function(original_tools_py):
        console.print(
            "[red]Error:[/red] infrastructure/entry_points/mcp_server/tools.py was generated by an older "
            "scaffold\n"
            "version and does not support --add-tool.\n"
            "[dim]Hint:[/dim] Make [cyan]async def bind_tools[/cyan] the last function in tools.py, or "
            "regenerate the entry point\n"
            "(back up any custom tools first) with [cyan]scaffold gep --type mcp[/cyan]."
        )
        raise typer.Exit(code=1)

    # Check test file has required structure
    if not mcp_tool_spec.has_test_registration_structure(original_test_tools_py):
        console.print(
            "[red]Error:[/red] tests/infrastructure/entry_points/mcp_server/test_tools.py is missing or "
            "does not have\n"
            "the structure --add-tool needs to append a registration test.\n"
            "[dim]Hint:[/dim] Restore test_tools.py, or regenerate the entry point with "
            "[cyan]scaffold gep --type mcp[/cyan]."
        )
        raise typer.Exit(code=1)

    # Check for duplicate tool names
    existing_names = mcp_tool_spec.find_existing_tool_names(original_tools_py)
    if tool_spec.name in existing_names:
        if tool_spec.name == "bind_tools":
            console.print(
                f"[red]Error:[/red] '{tool_spec.name}' is reserved by the tool-binding function and "
                "cannot be used as a tool name."
            )
        else:
            console.print(f"[red]Error:[/red] A tool named '{tool_spec.name}' already exists in tools.py.")
        raise typer.Exit(code=1)

    # T021: Render templates and append
    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        dry_run=dry_run,
    )

    # Render tool stub (4-space-indented nested function)
    tool_stub_content = builder.render(
        "entry_point/mcp/tool_stub.py.jinja2",
        {
            "name": tool_spec.name,
            "params": [{"name": p.name, "type": p.type} for p in tool_spec.params],
            "returns": tool_spec.returns,
            "docstring": tool_spec.docstring,
        },
    )

    # Render test stub
    test_stub_content = builder.render(
        "entry_point/mcp/test_tool_stub.py.jinja2",
        {"name": tool_spec.name},
    )

    # Safety check: ensure appended content will parse
    try:
        ast.parse(original_tools_py + tool_stub_content)
    except SyntaxError:
        console.print(
            "[red]Error:[/red] infrastructure/entry_points/mcp_server/tools.py cannot accept the new tool stub.\n"
            "[dim]Hint:[/dim] Regenerate the entry point with [cyan]scaffold gep --type mcp[/cyan]."
        )
        raise typer.Exit(code=1)

    # T030a: Check writability before any writes (FR-019)
    import os

    if not os.access(tools_py_path, os.W_OK):
        console.print(
            f"[red]Error:[/red] Cannot write to {tools_py_path.relative_to(project_root)}.\n"
            "[dim]Hint:[/dim] Check the file's permissions and re-run the command."
        )
        raise typer.Exit(code=1)

    if not os.access(test_tools_py_path, os.W_OK):
        console.print(
            f"[red]Error:[/red] Cannot write to {test_tools_py_path.relative_to(project_root)}.\n"
            "[dim]Hint:[/dim] Check the file's permissions and re-run the command."
        )
        raise typer.Exit(code=1)

    # Queue append operations
    builder.append_to_file(tools_py_path, tool_stub_content)
    builder.append_to_file(test_tools_py_path, test_stub_content)

    # T030a: Persist changes with restore-on-failure (FR-019)
    try:
        modified_paths = builder.persist()
    except OSError as e:
        # Restore original content
        try:
            tools_py_path.write_text(original_tools_py, encoding="utf-8")
            test_tools_py_path.write_text(original_test_tools_py, encoding="utf-8")
        except OSError:
            pass  # Best effort restore

        # Determine which file failed
        error_str = str(e).lower()
        if "test_tools" in error_str or str(test_tools_py_path) in str(e):
            failed_file = "test_tools.py"
        else:
            failed_file = "tools.py"

        console.print(
            f"[red]Error:[/red] Failed to write {failed_file} ({e}). "
            "tools.py was restored; no changes were made.\n"
            "[dim]Hint:[/dim] Fix the underlying problem (permissions, disk space) and re-run the command."
        )
        raise typer.Exit(code=1) from None

    if dry_run:
        console.print("\n[yellow]Dry run:[/yellow] Would modify:\n")
        for path in modified_paths:
            console.print(f"  • {path.relative_to(project_root)}")
        console.print("\n[yellow]Tool stub preview:[/yellow]")
        console.print(Syntax(tool_stub_content, "python", theme="monokai", line_numbers=False))
        console.print("\n[yellow]Test stub preview:[/yellow]")
        console.print(Syntax(test_stub_content, "python", theme="monokai", line_numbers=False))
    else:
        console.print(f"[green]✓[/green] Added tool '{tool_spec.name}' to MCP entry point.")


def _generate_entry_point_impl(
    type_: str,
    swagger: str | None,
    enable_kafka: bool,
    enable_mcp_client: bool,
    with_resources: bool,
    with_prompts: bool,
    add_tool: bool,
    name: str | None,
    param: list[str] | None,
    returns: str,
    description: str | None,
    dry_run: bool,
) -> None:
    # T016(b): Dispatch to --add-tool implementation if flag is set
    if add_tool:
        _add_tool_impl(
            type_,
            swagger,
            enable_kafka,
            enable_mcp_client,
            with_resources,
            with_prompts,
            name,
            param,
            returns,
            description,
            dry_run,
        )
        return

    # --- Validate type ---
    if type_ not in _REGISTRY:
        console.print(f"[red]Error:[/red] Unknown type '{type_}'. Allowed: {', '.join(_REGISTRY.keys())}.")
        raise typer.Exit(code=1) from None

    # --- Flag compatibility checks ---
    if swagger and type_ != "restapi":
        console.print("[red]Error:[/red] --swagger is only valid with --type restapi.")
        raise typer.Exit(code=1) from None

    if enable_mcp_client and type_ == "mcp":
        console.print("[red]Error:[/red] --enable-mcp-client is not valid with --type mcp.")
        raise typer.Exit(code=1) from None

    if (with_resources or with_prompts) and type_ != "mcp":
        console.print("[red]Error:[/red] --with-resources and --with-prompts are only valid with --type mcp.")
        raise typer.Exit(code=1) from None

    # --- Validate swagger path ---
    routes: list[tuple[str, str]] = []
    if swagger:
        swagger_path = Path(swagger)
        if not swagger_path.exists():
            console.print(f"[red]Error:[/red] Swagger file '{swagger}' not found.")
            raise typer.Exit(code=1) from None
        routes = _parse_swagger(swagger_path)

    # --- Locate project root ---
    try:
        project_root = find_project_root()
    except ScaffoldError:
        console.print("[red]Error:[/red] No scaffold-ca-python project found. Run 'scaffold ca' first.")
        raise typer.Exit(code=1) from None

    project_ctx = _load_project_context(project_root)

    # --- Compatibility guard (restapi vs mcp/agent) --------------------------
    if type_ == "restapi":
        pkg_ep = project_root / "src" / project_ctx.python_package / "infrastructure" / "entry_points"
        for incompatible in ("mcp_server", "agent"):
            conflict_dir = pkg_ep / incompatible
            if conflict_dir.exists():
                console.print(
                    f"[red]Error:[/red] Incompatible entry point '[bold]{incompatible}[/bold]' "
                    f"already exists at: {conflict_dir.relative_to(project_root)}\n"
                    "[dim]Hint:[/dim] A project may have only one entry-point type. "
                    f"Remove '{conflict_dir.relative_to(project_root)}' before adding restapi."
                )
                raise typer.Exit(code=1) from None

    if type_ in ("mcp", "agent"):
        restapi_dir = project_root / "src" / project_ctx.python_package / "infrastructure" / "entry_points" / "api"
        if restapi_dir.exists():
            console.print(
                f"[red]Error:[/red] Incompatible entry point '[bold]restapi[/bold]' "
                f"already exists at: {restapi_dir.relative_to(project_root)}\n"
                "[dim]Hint:[/dim] A project may have only one entry-point type. "
                f"Remove '{restapi_dir.relative_to(project_root)}' before adding {type_}."
            )
            raise typer.Exit(code=1) from None

    # --- Determine subdir and module context ---
    if type_ == "restapi":
        subdir = "api/v1"
    elif type_ == "mcp":
        subdir = "mcp_server"
    else:
        subdir = type_
    module_ctx = ModuleContext(
        name=type_.replace("-", "_"),
        layer=Layer.ENTRY_POINTS,
        project=project_ctx,
        subtype=type_,
    )

    pkg = project_ctx.python_package
    src_dir = project_root / "src" / pkg / "infrastructure" / "entry_points" / subdir

    # --- Duplicate guard ---
    if src_dir.exists():
        console.print(
            f"[red]Error:[/red] Directory '{src_dir.relative_to(project_root)}/' already exists.\n"
            "[dim]Hint:[/dim] Choose a different type or remove the existing directory first."
        )
        raise typer.Exit(code=1) from None

    # --- Create builder and get factory from registry ---
    builder = ModuleBuilder(
        project_root=project_root,
        project_ctx=project_ctx,
        module_ctx=module_ctx,
        dry_run=dry_run,
    )

    # Add flags to builder params for factory use
    builder.add_param("routes", routes)
    builder.add_param("enable_kafka", enable_kafka)
    builder.add_param("enable_mcp_client", enable_mcp_client)
    builder.add_param("with_resources", with_resources)
    builder.add_param("with_prompts", with_prompts)

    # Get factory class and instantiate
    factory_class = _REGISTRY[type_]
    factory = factory_class()

    # Invoke factory to build via ModuleBuilder
    factory.build(builder)

    # Persist all operations
    created = builder.persist()

    # --- Display results ---
    if dry_run:
        tree = Tree(f"[bold]{subdir}[/bold] (dry run)")
        for p in sorted(created):
            tree.add(str(p.relative_to(project_root)))
        console.print(tree)

        # Report any runtime dependencies queued for injection
        if builder.pending_dependencies:
            target = escape("[project.dependencies]")
            console.print(f"[dim]Would add to {target}: {', '.join(builder.pending_dependencies)}[/dim]")

        if type_ == "restapi":
            main_py = project_root / "src" / pkg / "main.py"
            if main_py.exists():
                console.print(f"[dim]Would delete: src/{pkg}/main.py[/dim]")
            console.print(f'[dim]Would update [project.scripts]: {pkg} = "{pkg}.server:start_server"[/dim]')
        else:
            console.print(f"[yellow]⚠[/yellow] main.py will be replaced with {type_} entrypoint.")
        return

    console.print(f"[green]✓[/green] Entry point [bold]{subdir}[/bold] created. Created {len(created)} file(s).")

    # --- Show results for special handling ---
    if type_ == "restapi":
        main_py = project_root / "src" / pkg / "main.py"
        if main_py.exists():
            console.print(f"[green]\u2713[/green] Deleted src/{pkg}/main.py")
        console.print(f'[green]\u2713[/green] Updated [project.scripts]: {pkg} = "{pkg}.server:start_server"')
    else:
        console.print(f"[yellow]⚠[/yellow] main.py replaced with {type_} entrypoint.")


def _parse_swagger(path: Path) -> list[tuple[str, str]]:
    """Parse an OpenAPI YAML/JSON file and return (path, method) pairs."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        raw: object = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    if not isinstance(raw, dict):
        return []
    paths_value = raw.get("paths", {})
    if not isinstance(paths_value, dict):
        return []
    result: list[tuple[str, str]] = []
    for route_path, methods in paths_value.items():
        if isinstance(methods, dict):
            for method in methods:
                if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                    result.append((str(route_path), method.lower()))
    return result


def register(app: typer.Typer) -> None:
    """Register gep / generate-entry-point commands onto *app*."""

    @app.command(
        "generate-entry-point",
        help=_GEP_HELP,
        epilog=_GEP_EPILOG,
    )
    @app.command("gep", hidden=True, help=_GEP_HELP, epilog=_GEP_EPILOG)
    def generate_entry_point(
        ctx: typer.Context,
        type_: Annotated[str | None, typer.Option("--type", help=_TYPE_HELP, rich_help_panel="Required")] = None,
        swagger: Annotated[str | None, typer.Option("--swagger", help=_SWAGGER_HELP, rich_help_panel="Options")] = None,
        enable_kafka: Annotated[
            bool,
            typer.Option(
                "--enable-kafka/--no-enable-kafka",
                help=_KAFKA_HELP,
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
        enable_mcp_client: Annotated[
            bool,
            typer.Option(
                "--enable-mcp-client/--no-enable-mcp-client",
                help=_MCP_CLIENT_HELP,
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
        with_resources: Annotated[
            bool,
            typer.Option(
                "--with-resources/--no-with-resources",
                help="Generate resources.py primitive (mcp only).",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
        with_prompts: Annotated[
            bool,
            typer.Option(
                "--with-prompts/--no-with-prompts",
                help="Generate prompts.py primitive (mcp only).",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
        add_tool: Annotated[
            bool,
            typer.Option(
                "--add-tool/--no-add-tool",
                help="Add a tool to an existing MCP entry point (mcp only).",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
        name: Annotated[str | None, typer.Option("--name", help="Tool name (required with --add-tool).")] = None,
        param: Annotated[
            list[str] | None,
            typer.Option("--param", help="Tool parameter in 'name:type' format (repeatable)."),
        ] = None,
        returns: Annotated[str, typer.Option("--returns", help="Tool return type.")] = "str",
        description: Annotated[
            str | None, typer.Option("--description", help="Tool description for docstring.")
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run/--no-dry-run",
                help="Preview without writing.",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
    ) -> None:
        """Scaffold an entry point inside infrastructure/entry_points/."""
        # T016(a): Check --add-tool without --type before the help shortcut
        if add_tool and type_ is None:
            console.print("[red]Error:[/red] --add-tool is only valid with --type mcp.")
            raise typer.Exit(code=1)

        if type_ is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_entry_point_impl(
            type_,
            swagger,
            enable_kafka,
            enable_mcp_client,
            with_resources,
            with_prompts,
            add_tool,
            name,
            param,
            returns,
            description,
            dry_run,
        )
