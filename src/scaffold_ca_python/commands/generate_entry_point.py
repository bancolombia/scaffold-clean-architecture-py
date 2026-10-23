"""generate_entry_point: scaffold an entry-point adapter and test stub."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._entry_point_rules import check_conflicts, check_flags
from scaffold_ca_python.commands._shared import (
    console,
    ensure_absent,
    fail,
    print_dry_run_tree,
    print_pending_dependencies,
    require_project_root,
)
from scaffold_ca_python.commands.add_mcp_tool import add_mcp_tool
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.openapi_routes import parse_routes
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.factory.entry_points import ENTRY_POINT_FACTORIES
from scaffold_ca_python.factory.entry_points.base import EntryPointFactory, EntryPointFlag
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer
from scaffold_ca_python.models.options import EntryPointOptions

_REGISTRY = ENTRY_POINT_FACTORIES  # backwards-compat alias for tests that patch it

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


@dataclass(frozen=True, slots=True)
class _BuildResult:
    factory: EntryPointFactory
    builder: ModuleBuilder
    subdir: str
    created: list[Path]


def _resolve_factory(options: EntryPointOptions) -> type[EntryPointFactory]:
    if options.type_ not in ENTRY_POINT_FACTORIES:
        fail(f"Unknown type '{options.type_}'. Allowed: {', '.join(ENTRY_POINT_FACTORIES.keys())}.")
    return ENTRY_POINT_FACTORIES[options.type_]


def _check_flags_for(options: EntryPointOptions, factory_class: type[EntryPointFactory]) -> None:
    active_flags: list[EntryPointFlag] = []
    if options.swagger is not None:
        active_flags.append(EntryPointFlag.SWAGGER)
    if options.enable_mcp_client:
        active_flags.append(EntryPointFlag.ENABLE_MCP_CLIENT)
    if options.with_resources or options.with_prompts:
        active_flags.append(EntryPointFlag.MCP_PRIMITIVES)
    if options.enable_kafka:
        active_flags.append(EntryPointFlag.ENABLE_KAFKA)
    check_flags(options.type_, factory_class, active_flags, ENTRY_POINT_FACTORIES)


def _load_routes(swagger: str | None) -> list[tuple[str, str]]:
    if swagger is None:
        return []
    path = Path(swagger)
    if not path.exists():
        fail(f"Swagger file '{swagger}' not found.")
    return parse_routes(path)


def _build(
    options: EntryPointOptions,
    factory_class: type[EntryPointFactory],
    project_root: Path,
    project_ctx: ProjectContext,
    routes: list[tuple[str, str]],
) -> _BuildResult:
    subdir = factory_class.subdir
    module_ctx = ModuleContext(
        name=options.type_.replace("-", "_"),
        layer=Layer.ENTRY_POINTS,
        project=project_ctx,
        subtype=options.type_,
    )
    src_dir = project_root / "src" / project_ctx.python_package / "infrastructure" / "entry_points" / subdir
    ensure_absent(
        src_dir,
        project_root,
        kind="Directory",
        hint="Choose a different type or remove the existing directory first.",
    )
    builder = ModuleBuilder(
        project_root=project_root, project_ctx=project_ctx, module_ctx=module_ctx, dry_run=options.dry_run
    )
    options.apply_to(builder, routes)
    factory = factory_class()
    factory.build(builder)
    created = builder.persist()
    return _BuildResult(factory=factory, builder=builder, subdir=subdir, created=created)


def _report(result: _BuildResult, options: EntryPointOptions, project_root: Path, pkg: str) -> None:
    if options.dry_run:
        print_dry_run_tree(result.subdir, result.created, project_root)
        print_pending_dependencies(result.builder)
        for note in result.factory.result_notes(project_root, pkg, options.type_, dry_run=True):
            console.print(note)
        return
    console.print(
        f"[green]✓[/green] Entry point [bold]{result.subdir}[/bold] created. Created {len(result.created)} file(s)."
    )
    for note in result.factory.result_notes(project_root, pkg, options.type_, dry_run=False):
        console.print(note)


def _generate_entry_point(options: EntryPointOptions) -> None:
    if options.add_tool:
        add_mcp_tool(options)
        return
    factory_class = _resolve_factory(options)
    _check_flags_for(options, factory_class)
    routes = _load_routes(options.swagger)
    project_root = require_project_root()
    project_ctx = load_project_context(project_root)
    pkg = project_ctx.python_package
    check_conflicts(project_root, pkg, options.type_, factory_class)
    result = _build(options, factory_class, project_root, project_ctx, routes)
    _report(result, options, project_root, pkg)


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
        if add_tool and type_ is None:
            console.print("[red]Error:[/red] --add-tool is only valid with --type mcp.")
            raise typer.Exit(code=1)

        if type_ is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)

        options = EntryPointOptions(
            type_=type_,
            swagger=swagger,
            enable_kafka=enable_kafka,
            enable_mcp_client=enable_mcp_client,
            with_resources=with_resources,
            with_prompts=with_prompts,
            add_tool=add_tool,
            name=name,
            params=tuple(param or []),
            returns=returns,
            description=description,
            dry_run=dry_run,
        )
        _generate_entry_point(options)
