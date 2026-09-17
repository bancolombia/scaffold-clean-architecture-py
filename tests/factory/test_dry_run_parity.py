"""Dry-run path parity against the captured baseline (T043 / SC-005).

For each type of both entry-point (`gep`) and driven-adapter (`gda`) commands, the set
of paths a dry-run would touch must match a golden baseline fixture. The baseline is
regenerated from the real factory output and pins the file-generation contract; an
accidental change to any factory's queued paths breaks these tests, prompting a
deliberate baseline refresh.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.commands import generate_driven_adapter, generate_entry_point
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.factory import ModuleFactory
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer

runner = CliRunner()

_BASELINE: dict[str, list[str]] = json.loads(
    (Path(__file__).parent / "fixtures" / "dry_run_baseline.json").read_text(encoding="utf-8")
)

# Flags the gep command always attaches to the builder before invoking a factory.
_GEP_PARAMS = {
    "routes": [],
    "enable_kafka": False,
    "enable_mcp_client": False,
    "with_resources": False,
    "with_prompts": False,
}


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Scaffold a real `my-app` project (package `my_app`) inside tmp_path."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    return project_dir


def _preview(
    root: Path,
    module_ctx: ModuleContext,
    factory_cls: type[ModuleFactory],
    params: dict[str, object] | None = None,
) -> list[str]:
    """Return the sorted relative paths a factory dry-run would touch."""
    builder = ModuleBuilder(
        project_root=root,
        project_ctx=ProjectContext(name="my-app"),
        module_ctx=module_ctx,
        dry_run=True,
    )
    for key, value in (params or {}).items():
        builder.add_param(key, value)
    factory_cls().build(builder)
    return sorted(p.relative_to(root).as_posix() for p in builder.persist())


@pytest.mark.parametrize("type_", ["restapi", "agent", "mcp", "generic"])
def test_gep_dry_run_parity(project_root: Path, type_: str) -> None:
    module_ctx = ModuleContext(
        name=type_.replace("-", "_"),
        layer=Layer.ENTRY_POINTS,
        project=ProjectContext(name="my-app"),
        subtype=type_,
    )
    preview = _preview(project_root, module_ctx, generate_entry_point._REGISTRY[type_], _GEP_PARAMS)
    assert preview == _BASELINE[f"gep:{type_}"]


@pytest.mark.parametrize(
    ("type_", "name"),
    [("rest-consumer", None), ("secrets", None), ("generic", "my-adapter")],
)
def test_gda_dry_run_parity(project_root: Path, type_: str, name: str | None) -> None:
    proj = ProjectContext(name="my-app")
    if type_ == "rest-consumer":
        module_ctx = ModuleContext(name="rest_consumer", layer=Layer.DRIVEN_ADAPTERS, project=proj)
    elif type_ == "secrets":
        module_ctx = ModuleContext(name="secrets", layer=Layer.DRIVEN_ADAPTERS, project=proj)
    else:
        assert name is not None
        module_ctx = ModuleContext(name=name, layer=Layer.DRIVEN_ADAPTERS, project=proj)
    preview = _preview(project_root, module_ctx, generate_driven_adapter._REGISTRY[type_])
    assert preview == _BASELINE[f"gda:{type_}"]
