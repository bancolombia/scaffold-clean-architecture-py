"""generate_project: scaffold a full Clean Architecture project skeleton."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import (
    DryRunProject,
    console,
    fail,
    print_dry_run_tree,
    register_with_alias,
    show_help_if_missing,
)
from scaffold_ca_python.core.errors import ScaffoldError
from scaffold_ca_python.core.file_writer import FileWriter
from scaffold_ca_python.core.name_utils import to_snake_case, validate_name
from scaffold_ca_python.core.template_renderer import TemplateRenderer
from scaffold_ca_python.core.version import get_scaffold_version
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

_DI_CONFIG_FILES_WIREUP: tuple[str, ...] = (
    "__init__.py",
    "config.py",
    "wiring.py",
)

# Layers: (subpath-under-src/<pkg>, label for layer_init.jinja2)
_LAYER_DIRS: tuple[tuple[str, str], ...] = (
    ("application", "application"),
    ("domain/model", "domain/model"),
    ("domain/usecase", "domain/usecase"),
    ("infrastructure/driven_adapters", "infrastructure/driven_adapters"),
    ("infrastructure/entry_points", "infrastructure/entry_points"),
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
    scaffold_version = get_scaffold_version()
    ctx_dict = ProjectContext(name=name, scaffold_version=scaffold_version).model_dump()
    ctx_dict["created_at"] = datetime.now(tz=UTC).isoformat()

    files: list[tuple[Path, str]] = []

    for filename, template in _ROOT_FILES:
        files.append((target_dir / filename, renderer.render(template, ctx_dict)))

    di_cfg = target_dir / "src" / python_pkg / "application" / "config"
    for fname in _DI_CONFIG_FILES_WIREUP:
        files.append((di_cfg / fname, renderer.render(f"project/application/config/{fname}.jinja2", ctx_dict)))
    # usecases/ package scanned by wireup
    files.append(
        (
            di_cfg / "usecases" / "__init__.py",
            renderer.render("project/application/config/usecases/__init__.py.jinja2", ctx_dict),
        )
    )

    src_pkg = target_dir / "src" / python_pkg
    files.append((src_pkg / "main.py", renderer.render("project/main.py.jinja2", ctx_dict)))
    files.append((src_pkg / "__init__.py", renderer.render("project/package_init.py.jinja2", {"name": name})))

    for layer_path, layer_label in _LAYER_DIRS:
        layer_ctx = {**ctx_dict, "layer": layer_label}
        files.append((src_pkg / layer_path / "__init__.py", renderer.render("project/layer_init.jinja2", layer_ctx)))

    tests_root = target_dir / "src" / "tests"
    files.append((tests_root / "__init__.py", renderer.render("project/empty.jinja2", {})))
    files.append((tests_root / "test_main.py", renderer.render("project/test_main.py.jinja2", ctx_dict)))

    tests_app_cfg = tests_root / "application" / "config"
    files.append((tests_root / "application" / "__init__.py", renderer.render("project/empty.jinja2", {})))
    files.append((tests_app_cfg / "__init__.py", renderer.render("project/empty.jinja2", {})))
    files.append((tests_app_cfg / "test_config.py", renderer.render("project/test_config.py.jinja2", ctx_dict)))
    files.append((tests_app_cfg / "test_wiring.py", renderer.render("project/test_wiring.py.jinja2", ctx_dict)))
    files.append((tests_app_cfg / "usecases" / "__init__.py", renderer.render("project/empty.jinja2", {})))
    return files


def _generate_project_impl(
    name: str,
    dry_run: bool,
    *,
    renderer: TemplateRenderer | None = None,
    writer: FileWriter | None = None,
) -> None:
    try:
        validate_name(name)
    except ScaffoldError as exc:
        fail(str(exc))

    python_pkg = to_snake_case(name)
    target_dir = Path.cwd() / name

    if target_dir.exists():
        fail(
            f"Directory '{name}/' already exists. Aborting to prevent data loss.",
            hint="Choose a different project name or remove the existing directory first.",
        )

    _renderer = renderer or TemplateRenderer()
    _writer = writer or FileWriter()
    files = _collect_files(name, python_pkg, target_dir, _renderer)

    if dry_run:
        print_dry_run_tree(f"{name}/", [p for p, _ in files], target_dir)
        return

    for path, content in files:
        _writer.write(path, content)

    console.print(f"[green]✓[/green] Project [bold]{name}/[/bold] created successfully. Created {len(files)} file(s).")


def register(app: typer.Typer) -> None:
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
        dry_run: DryRunProject = False,
    ) -> None:
        name = show_help_if_missing(ctx, name)
        _generate_project_impl(name, dry_run)

    register_with_alias(app, "clean-architecture", "ca", clean_architecture, help=_GCA, epilog=_GCA_EPILOG)
