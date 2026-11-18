"""Tests for ModuleBuilder foundational behavior."""

from __future__ import annotations

from pathlib import Path

import pytest

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import write_minimal_pyproject


class _StubRenderer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def render(self, template_name: str, context: object) -> str:
        self.calls.append((template_name, context))
        return "# rendered"


class _FilesystemReadingFactory:
    def __init__(self, probe: Path) -> None:
        self._probe = probe

    def build(self, builder: ModuleBuilder) -> None:
        # The call below must execute even when builder.dry_run is True.
        builder.add_param("probe_exists", self._probe.exists())


def _project_ctx() -> ProjectContext:
    return ProjectContext(name="ms-demo")


def _module_ctx(project: ProjectContext) -> ModuleContext:
    return ModuleContext(name="health", project=project)


def test_add_file_and_dry_run_returns_preview_without_writing(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, module_ctx=_module_ctx(project), dry_run=True)

    target = tmp_path / "src" / "ms_demo" / "domain" / "model" / "health.py"
    builder.add_file(target, "class Health: pass\n")

    preview = builder.persist()

    assert target in preview
    assert not target.exists()


def test_delete_file_operation_is_included_in_preview(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    target = tmp_path / "obsolete.py"
    builder.delete_file(target)

    preview = builder.persist()

    assert target in preview


def test_add_dependency_and_real_persist_injects_dependency(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)

    builder.add_dependency("httpx>=0.27")

    _ = builder.persist()
    pyproject = (tmp_path / "pyproject.toml").read_text(encoding="utf-8")

    assert "httpx>=0.27" in pyproject


def test_add_param_and_get_param_round_trip(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    builder.add_param("k", "v")

    assert builder.get_param("k") == "v"
    assert builder.get_param("missing", "default") == "default"


def test_render_delegates_to_template_renderer(tmp_path: Path) -> None:
    project = _project_ctx()
    stub = _StubRenderer()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True, template_renderer=stub)  # type: ignore[arg-type]

    out = builder.render("x.jinja2", {"a": 1})

    assert out == "# rendered"
    assert stub.calls == [("x.jinja2", {"a": 1})]


def test_persist_real_writes_file(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)

    target = tmp_path / "a.py"
    builder.add_file(target, "# ok\n")

    written = builder.persist()

    assert target in written
    assert target.read_text(encoding="utf-8") == "# ok\n"


def test_filesystem_read_in_factory_runs_during_dry_run(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    probe = tmp_path / "probe.flag"
    probe.write_text("x", encoding="utf-8")

    factory = _FilesystemReadingFactory(probe)
    factory.build(builder)
    _ = builder.persist()

    assert builder.get_param("probe_exists") is True


# insert_after


def test_insert_after_is_included_in_dry_run_preview(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    target = tmp_path / "config.py"
    target.write_text('LOG_LEVEL: str = "INFO"\n', encoding="utf-8")
    builder.insert_after(target, anchor="LOG_LEVEL", content='HOST: str = "0.0.0.0"')

    preview = builder.persist()

    assert target in preview
    # dry-run must not modify the file
    assert "HOST" not in target.read_text(encoding="utf-8")


def test_insert_after_real_persist_modifies_file(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)

    target = tmp_path / "config.py"
    target.write_text(
        'class Settings:\n    LOG_LEVEL: str = "INFO"\n    model_config = None\n',
        encoding="utf-8",
    )
    builder.insert_after(
        target,
        anchor="LOG_LEVEL",
        content='    HOST: str = "0.0.0.0"\n    PORT: int = 8000',
    )
    builder.persist()

    text = target.read_text(encoding="utf-8")
    lines = text.splitlines()
    log_idx = next(i for i, line in enumerate(lines) if "LOG_LEVEL" in line)
    assert "HOST" in lines[log_idx + 1]
    assert "PORT" in lines[log_idx + 2]


# add_dependency with group


def test_add_dependency_with_group_injects_into_group(tmp_path: Path) -> None:
    import tomllib

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)

    builder.add_dependency("respx>=0.22", group="test")

    _ = builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    test_entries = [e for e in data.get("dependency-groups", {}).get("test", []) if isinstance(e, str)]
    assert any("respx" in e for e in test_entries), f"respx not in test group: {test_entries}"


def test_add_dependency_with_group_does_not_touch_runtime_deps(tmp_path: Path) -> None:
    import tomllib

    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)

    builder.add_dependency("respx>=0.22", group="test")

    _ = builder.persist()

    with (tmp_path / "pyproject.toml").open("rb") as fh:
        data = tomllib.load(fh)
    runtime_deps: list[str] = data.get("project", {}).get("dependencies", [])
    assert not any("respx" in d for d in runtime_deps), "respx must not appear in runtime deps"


def test_add_dependency_with_group_dry_run_does_not_write(tmp_path: Path) -> None:
    write_minimal_pyproject(tmp_path, with_dependency_groups=True)
    pyproject = tmp_path / "pyproject.toml"
    original = pyproject.read_bytes()
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    builder.add_dependency("respx>=0.22", group="test")
    _ = builder.persist()

    assert pyproject.read_bytes() == original


def test_pending_dependencies_properties_expose_queued_deps(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    builder.add_dependency("httpx>=0.27")
    builder.add_dependency("respx>=0.22", group="test")

    assert builder.pending_dependencies == ["httpx>=0.27"]
    assert builder.pending_group_dependencies == {"test": ["respx>=0.22"]}


def test_pending_properties_return_copies(tmp_path: Path) -> None:
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)

    builder.add_dependency("httpx>=0.27")
    builder.add_dependency("respx>=0.22", group="test")

    # Mutating the returned values must not affect internal state.
    builder.pending_dependencies.append("evil>=9")
    builder.pending_group_dependencies["test"].append("evil>=9")
    builder.pending_group_dependencies["new"] = ["evil>=9"]

    assert builder.pending_dependencies == ["httpx>=0.27"]
    assert builder.pending_group_dependencies == {"test": ["respx>=0.22"]}


# : set_project_script API


def _write_pyproject_with_scripts(root: Path) -> None:
    (root / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\ndependencies = []\n\n[project.scripts]\n',
        encoding="utf-8",
    )


def test_set_project_script_default_sets_start_server(tmp_path: Path) -> None:
    """set_project_script() sets pending_project_script to 'start_server'."""
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)
    assert builder.pending_project_script is None
    builder.set_project_script()
    assert builder.pending_project_script == "start_server"


def test_set_project_script_custom_value(tmp_path: Path) -> None:
    """set_project_script('main') sets pending_project_script to 'main'."""
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)
    builder.set_project_script("main")
    assert builder.pending_project_script == "main"


def test_without_set_project_script_persist_does_not_touch_scripts(tmp_path: Path) -> None:
    """Without a set_project_script call, [project.scripts] is not modified."""

    _write_pyproject_with_scripts(tmp_path)
    original = (tmp_path / "pyproject.toml").read_bytes()
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)
    builder.persist()
    assert (tmp_path / "pyproject.toml").read_bytes() == original


def test_set_project_script_persist_calls_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """persist() calls update_project_scripts when set_project_script was called."""
    import scaffold_ca_python.core.module_builder as mb  # noqa: PLC0415

    calls: list[tuple[object, ...]] = []

    def _fake_update(
        root: Path,
        ctx: object,
        entry_fn: str = "start_server",
        *,
        dry_run: bool = False,
    ) -> bool:
        calls.append((root, ctx, entry_fn, dry_run))
        return True

    monkeypatch.setattr(mb, "update_project_scripts", _fake_update)
    _write_pyproject_with_scripts(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=False)
    builder.set_project_script("main")
    builder.persist()
    assert calls != [], "update_project_scripts was not called"
    assert calls[0][2] == "main"
    assert calls[0][3] is False


def test_set_project_script_dry_run_calls_dry_run_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In dry-run, persist() calls update_project_scripts with dry_run=True."""
    import scaffold_ca_python.core.module_builder as mb  # noqa: PLC0415

    calls: list[tuple[object, ...]] = []

    def _fake_update(
        root: Path,
        ctx: object,
        entry_fn: str = "start_server",
        *,
        dry_run: bool = False,
    ) -> bool:
        calls.append((root, ctx, entry_fn, dry_run))
        return True

    monkeypatch.setattr(mb, "update_project_scripts", _fake_update)
    _write_pyproject_with_scripts(tmp_path)
    project = _project_ctx()
    builder = ModuleBuilder(project_root=tmp_path, project_ctx=project, dry_run=True)
    builder.set_project_script()
    builder.persist()
    assert calls != [], "update_project_scripts was not called"
    assert calls[0][3] is True
