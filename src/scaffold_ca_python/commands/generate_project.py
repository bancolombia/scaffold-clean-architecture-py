"""generate_project: scaffold a full Clean Architecture project skeleton."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import console, fail
from scaffold_ca_python.core.file_writer import FileWriter
from scaffold_ca_python.core.name_utils import ScaffoldError, to_snake_case, validate_name
from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.models.context import ProjectContext

_ROOT_FILES: tuple[tuple[str, str], ...] = (
    ("pyproject.toml", "project/pyproject_toml.jinja2"),
    ("README.md", "project/README.jinja2"),
    (".gitignore", "project/gitignore.jinja2"),
    ("mypy.ini", "project/mypy_ini.jinja2"),
    ("Dockerfile", "project/dockerfile.jinja2"),
    (".dockerignore", "project/dockerignore.jinja2"),
    (".python-version", "project/python_version.jinja2"),
)

_DI_CONFIG_FILES: tuple[str, ...] = (
    "__init__.py",
    "config.py",
    "resource_container.py",
    "driven_adapters_container.py",
    "usecases_container.py",
    "container.py",
)

# Layers: (subpath-under-src/<pkg>, label for layer_init.jinja2)
_LAYER_DIRS: tuple[tuple[str, str], ...] = (
    ("application", "application"),
    ("domain/model", "domain/model"),
    ("domain/usecase", "domain/usecase"),
    ("infrastructure/driven_adapters", "infrastructure/driven-adapters"),
    ("infrastructure/entry_points", "infrastructure/entry-points"),
    ("infrastructure/helpers", "infrastructure/helpers"),
)

_GCA = "Scaffold a new Clean Architecture project. Alias: 'ca'"
_GCA_EPILOG = "Examples:\n\n    * scaffold ca --name my-project\n\n  * scaffold clean-architecture --name my_project"


def _collect_files(
    name: str,
    python_pkg: str,
    target_dir: Path,
    renderer: TemplateRenderer,
) -> list[tuple[Path, str]]:
    """Return all (path, content) pairs for a new project scaffold."""
    ctx_dict = ProjectContext(name=name).model_dump()
    ctx_dict["created_at"] = datetime.now(tz=UTC).isoformat()

    files: list[tuple[Path, str]] = []

    for filename, template in _ROOT_FILES:
        files.append((target_dir / filename, renderer.render(template, ctx_dict)))

    di_cfg = target_dir / "src" / python_pkg / "application" / "config"
    for fname in _DI_CONFIG_FILES:
        files.append((di_cfg / fname, renderer.render(f"project/application/config/{fname}.jinja2", ctx_dict)))

    src_pkg = target_dir / "src" / python_pkg
    files.append((src_pkg / "main.py", renderer.render("project/main.py.jinja2", ctx_dict)))
    files.append((src_pkg / "__init__.py", renderer.render("project/package_init.py.jinja2", {"name": name})))

    for layer_path, layer_label in _LAYER_DIRS:
        layer_ctx = {**ctx_dict, "layer": layer_label}
        files.append((src_pkg / layer_path / "__init__.py", renderer.render("project/layer_init.jinja2", layer_ctx)))

    files.append((target_dir / "src" / "tests" / "__init__.py", renderer.render("project/empty.jinja2", {})))
    return files


def _generate_project_impl(
    name: str | None,
    dry_run: bool,
    *,
    renderer: TemplateRenderer | None = None,
    writer: FileWriter | None = None,
) -> None:
    if name is None:
        return

    try:
        validate_name(name)
    except ScaffoldError as exc:
        fail(str(exc))

    python_pkg = to_snake_case(name)
    target_dir = Path.cwd() / name

    if target_dir.exists():
        fail(
            f"Directory '{python_pkg}/' already exists. Aborting to prevent data loss.",
            hint="Choose a different project name or remove the existing directory first.",
        )

    _renderer = renderer or TemplateRenderer()
    _writer = writer or FileWriter()
    files = _collect_files(name, python_pkg, target_dir, _renderer)

    if dry_run:
        from rich.tree import Tree

        tree = Tree(f"[bold]{python_pkg}/[/bold] (dry run)")
        for path, _ in sorted(files, key=lambda t: t[0]):
            try:
                tree.add(str(path.relative_to(target_dir)))
            except ValueError:
                tree.add(str(path))
        console.print(tree)
        return

    for path, content in files:
        _writer.write(path, content)

    console.print(
        f"[green]✓[/green] Project [bold]{python_pkg}/[/bold] created successfully. Created {len(files)} file(s)."
    )


def register(app: typer.Typer) -> None:
    """Register clean-architecture / ca commands onto *app*."""

    @app.command(
        "clean-architecture",
        help=_GCA,
        epilog=_GCA_EPILOG,
    )
    @app.command(
        "ca",
        hidden=True,
        help=_GCA,
        epilog=_GCA_EPILOG,
    )
    def clean_architecture(
        ctx: typer.Context,
        name: Annotated[
            str | None,
            typer.Option(
                "--name",
                help="Project name (kebab-case or snake_case).",
                rich_help_panel="Required",
            ),
        ] = None,
        dry_run: Annotated[
            bool,
            typer.Option(
                "--dry-run/--no-dry-run",
                help="Preview files without writing.",
                rich_help_panel="Options",
                show_default=True,
            ),
        ] = False,
    ) -> None:
        """Scaffold a complete Clean Architecture Python project."""
        if name is None:
            typer.echo(ctx.get_help())
            raise typer.Exit(0)
        _generate_project_impl(name, dry_run)
