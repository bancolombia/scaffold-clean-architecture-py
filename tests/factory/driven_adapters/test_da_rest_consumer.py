"""Tests for DrivenAdapterRestConsumer factory."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="rest-consumer", project=project)


def test_rest_consumer_files_queued_in_dry_run(tmp_path: Path) -> None:
    """: Verify DrivenAdapterRestConsumer.build() queues expected files."""
    write_minimal_pyproject(tmp_path)
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
    """: Verify DrivenAdapterRestConsumer adds httpx (runtime) and respx (test group)."""
    import tomllib

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
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


def test_rest_consumer_template_has_injectable(tmp_path: Path) -> None:
    """-: rest_consumer adapter must have @injectable from wireup."""
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext

    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", project=project)
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
    """-: rest_consumer must generate a RestConsumerSettings file."""
    from scaffold_ca_python.core.module_builder import ModuleBuilder
    from scaffold_ca_python.models.context import ModuleContext, ProjectContext

    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", project=project)
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


#  (.3): Template quality — imports, conftest, no **kwargs


def _render_adapter(tmp_path: Path, gateway: object | None = None) -> str:
    """Render rest_consumer.py.jinja2 and return its content."""
    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    if gateway is not None:
        builder.add_param("gateway", gateway)
    DrivenAdapterRestConsumer().build(builder)
    builder.persist()

    adapter_file = (
        tmp_path / "src" / "ms_demo" / "infrastructure" / "driven_adapters" / "rest_consumer" / "rest_consumer.py"
    )
    return adapter_file.read_text(encoding="utf-8")


def test_rest_consumer_no_double_blank_lines_between_imports(tmp_path: Path) -> None:
    """: Without gateway, import wireup must be directly followed by from-import (no stray blank)."""
    content = _render_adapter(tmp_path)
    lines = content.splitlines()
    wireup_idx = next(i for i, ln in enumerate(lines) if ln == "import wireup")
    next_content = next(ln for ln in lines[wireup_idx + 1 :] if ln.strip())
    assert next_content.startswith("from "), (
        f"Expected 'from' import immediately after 'import wireup', got: {next_content!r}\n\n{content}"
    )


def test_rest_consumer_gateway_no_double_blank_lines_between_imports(tmp_path: Path) -> None:
    """: With gateway, gateway import must directly follow wireup import (no stray blank from {%- if %})."""
    from types import SimpleNamespace

    gw = SimpleNamespace(
        name="book_repository",
        class_name="BookRepository",
        model_module="book",
    )
    content = _render_adapter(tmp_path, gateway=gw)
    lines = content.splitlines()
    wireup_idx = next(i for i, ln in enumerate(lines) if ln == "import wireup")
    next_content = next(ln for ln in lines[wireup_idx + 1 :] if ln.strip())
    assert next_content.startswith("from "), (
        f"Expected gateway 'from' import after 'import wireup', got: {next_content!r}\n\n{content}"
    )


def test_rest_consumer_no_kwargs_object(tmp_path: Path) -> None:
    """: Generated rest_consumer.py must not contain **kwargs: object."""
    content = _render_adapter(tmp_path)
    assert "**kwargs" not in content, "rest_consumer.py.jinja2 must not render **kwargs"


def test_rest_consumer_conftest_fixture_appended(tmp_path: Path) -> None:
    """: gda rest-consumer must create/append REST_CONSUMER_BASE_URL fixture in conftest.py."""
    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer

    DrivenAdapterRestConsumer().build(builder)
    builder.persist()

    conftest_path = tmp_path / "src" / "tests" / "conftest.py"
    assert conftest_path.exists(), "conftest.py must be created by gda rest-consumer"
    content = conftest_path.read_text(encoding="utf-8")
    assert "rest_consumer_env" in content, "conftest.py must contain rest_consumer_env fixture"
    assert "REST_CONSUMER_BASE_URL" in content, "conftest.py must set REST_CONSUMER_BASE_URL"
    assert "autouse=True" in content, "conftest.py fixture must be autouse"


def test_rest_consumer_conftest_fixture_is_idempotent(tmp_path: Path) -> None:
    """: Calling _append_rest_consumer_conftest twice must not duplicate the fixture."""
    from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import _append_rest_consumer_conftest

    write_minimal_pyproject(tmp_path)
    project = ProjectContext(name="ms-demo")
    module_ctx = ModuleContext(name="rest_consumer", project=project)
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=module_ctx, dry_run=False)

    conftest_path = tmp_path / "src" / "tests" / "conftest.py"
    _append_rest_consumer_conftest(builder, conftest_path)
    builder.persist()
    _append_rest_consumer_conftest(builder, conftest_path)
    builder.persist()

    content = conftest_path.read_text(encoding="utf-8")
    assert content.count("rest_consumer_env") == 1, "conftest.py fixture must not be duplicated"
