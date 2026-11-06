"""Shared test utilities (import directly; not pytest fixtures)."""

from __future__ import annotations

import os
import re
from pathlib import Path

from typer.testing import CliRunner, Result

from scaffold_ca_python.cli import app
from scaffold_ca_python.core.project_detector import load_project_context
from scaffold_ca_python.models.context import ModuleContext, ProjectContext

runner = CliRunner()


def invoke_in(cwd: Path, *cli_args: str) -> Result:
    """Run scaffold CLI in-process with a temporary working directory."""
    old = os.getcwd()
    try:
        os.chdir(cwd)
        return runner.invoke(app, list(cli_args), catch_exceptions=False)
    finally:
        os.chdir(old)


def write_minimal_pyproject(
    root: Path,
    *,
    project_name: str = "demo",
    with_dependency_groups: bool = False,
) -> None:
    """Minimal pyproject.toml so ModuleBuilder can resolve a package layout."""
    body = f"""
[project]
name = "{project_name}"
version = "0.1.0"
dependencies = []
""".strip()
    if with_dependency_groups:
        body += """

[dependency-groups]
test = [
    "pytest==9.1.1",
]
dev = [
    "ruff==0.16.8",
    {include-group = "test"},
]"""
    (root / "pyproject.toml").write_text(body + "\n", encoding="utf-8")


def read_template(relative_path: str) -> str:
    """Read a scaffold template file by path under templates/."""
    templates = Path(__file__).resolve().parent.parent / "src" / "scaffold_ca_python" / "templates"
    return (templates / relative_path).read_text(encoding="utf-8")


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def project_ctx(project_root: Path) -> ProjectContext:
    return load_project_context(project_root)


def module_ctx(project_root: Path, name: str) -> ModuleContext:
    return ModuleContext(name=name, project=project_ctx(project_root))
