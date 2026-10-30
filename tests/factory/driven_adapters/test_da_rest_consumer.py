"""Tests for DrivenAdapterRestConsumer factory (T024)."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from scaffold_ca_python.models.layer import Layer


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="rest-consumer", layer=Layer.DRIVEN_ADAPTERS, project=project)


def _write_minimal_pyproject(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        """
[project]
name = "demo"
version = "0.1.0"
dependencies = []

[dependency-groups]
test = [
    "pytest==9.1.1",
]
dev = [
    "ruff==0.16.8",
    {include-group = "test"},
]
""".strip()
        + "\n",
        encoding="utf-8",
    )


def test_rest_consumer_files_queued_in_dry_run(tmp_path: Path) -> None:
    """T024: Verify DrivenAdapterRestConsumer.build() queues expected files."""
    _write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=True)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    factory = DrivenAdapterRestConsumer()
    factory.build(builder)

    preview = builder.persist()

    # Verify all rest-consumer files are queued:
    # - src: __init__.py, rest_consumer.py
    # - tests: test_rest_consumer.py

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "rest_consumer"
    test_dir = tmp_path / "src" / "tests" / "infrastructure" / "driven_adapters" / "rest_consumer"

    expected_files = [
        src_dir / "__init__.py",
        src_dir / "rest_consumer.py",
        test_dir / "test_rest_consumer.py",
    ]

    for expected in expected_files:
        assert expected in preview, f"Expected {expected.relative_to(tmp_path)} in preview"


def test_rest_consumer_dependencies_injected(tmp_path: Path) -> None:
    """T024: Verify DrivenAdapterRestConsumer adds httpx (runtime) and respx (test group)."""
    import tomllib

    _write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=False)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    factory = DrivenAdapterRestConsumer()
    factory.build(builder)

    _ = builder.persist()
    pyproject_text = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    # Verify httpx runtime dep is present
    assert "httpx~=0.28.1" in pyproject_text, "Expected httpx~=0.28.1 in [project.dependencies]"

    # Verify respx is injected into [dependency-groups.test]
    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    test_entries = data.get("dependency-groups", {}).get("test", [])
    test_strings = [e for e in test_entries if isinstance(e, str)]
    assert any("respx" in e for e in test_strings), f"Expected respx in [dependency-groups.test], got: {test_strings}"

    # Verify include-group in dev group was preserved
    dev_entries = data.get("dependency-groups", {}).get("dev", [])
    include_entries = [e for e in dev_entries if isinstance(e, dict)]
    assert any(e.get("include-group") == "test" for e in include_entries), (
        "include-group entry was lost from [dependency-groups.dev]"
    )


# ---------------------------------------------------------------------------
# T026 (US1): RestConsumer wireup changes — must FAIL until T023-T024
# ---------------------------------------------------------------------------


def test_rest_consumer_template_has_injectable(tmp_path: Path) -> None:
    """T023-T024: rest_consumer adapter must have @injectable from wireup."""
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext
    from scaffold_ca_python.models.layer import Layer

    _write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", layer=Layer.DRIVEN_ADAPTERS, project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    DrivenAdapterRestConsumer().build(builder)
    builder.persist()

    adapter_file = (
        tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "rest_consumer" / "rest_consumer.py"
    )
    content = adapter_file.read_text()
    assert "wireup" in content or "@injectable" in content, "RestConsumer adapter must have @injectable"


def test_rest_consumer_settings_file_generated(tmp_path: Path) -> None:
    """T023-T024: rest_consumer must generate a RestConsumerSettings file."""
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext
    from scaffold_ca_python.models.layer import Layer

    _write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", layer=Layer.DRIVEN_ADAPTERS, project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    DrivenAdapterRestConsumer().build(builder)
    builder.persist()

    src_dir = tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "rest_consumer"
    settings_candidates = list(src_dir.glob("*settings*.py")) + list(src_dir.glob("*config*.py"))
    assert settings_candidates, "RestConsumer must generate a settings or config file"
    combined = " ".join(f.read_text() for f in settings_candidates)
    assert "BaseSettings" in combined, "Settings file must use pydantic-settings BaseSettings"
    assert "base_url" in combined.lower(), "Settings must have a base_url field"
