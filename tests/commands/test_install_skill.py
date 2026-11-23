"""`scaffold install-skill`: packaged skill names, targets, --force and AGENTS.md."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from scaffold_ca_python.commands.install_skill import packaged_skills

runner = CliRunner()


def _invoke(*args: str) -> object:
    return runner.invoke(app, ["install-skill", *args], catch_exceptions=False)


def test_migrate_di_is_packaged_with_references() -> None:
    assert "migrate-di" in packaged_skills()
    root = Path(__file__).resolve().parents[2] / "src" / "scaffold_ca_python" / "skills" / "migrate-di"
    references = ("recipes.md", "errors.md", "checklist.md", "pre-scaffold.md")
    for rel in ("SKILL.md", *(f"references/{name}" for name in references)):
        assert (root / rel).is_file(), rel


@pytest.mark.parametrize("name", ["../commands", "..", "commands", "missing"])
def test_unknown_or_traversal_skill_is_rejected(project_root: Path, name: str) -> None:
    result = _invoke(name)
    assert result.exit_code == 1  # type: ignore[attr-defined]
    assert "Unknown skill" in result.output  # type: ignore[attr-defined]
    assert not any((project_root / d).exists() for d in (".claude", ".cursor", ".agents"))


def test_all_targets_are_populated(project_root: Path) -> None:
    result = _invoke("migrate-di")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    for d in (".claude/skills", ".cursor/skills", ".agents/skills"):
        assert (project_root / d / "migrate-di" / "SKILL.md").is_file()
    agents = (project_root / "AGENTS.md").read_text(encoding="utf-8")
    assert "`.claude/skills/migrate-di/SKILL.md`" in agents
    assert "`.agents/skills/migrate-di/SKILL.md`" in agents


def test_single_target(project_root: Path) -> None:
    assert _invoke("migrate-di", "--target", "claude").exit_code == 0  # type: ignore[attr-defined]
    assert (project_root / ".claude/skills/migrate-di/SKILL.md").is_file()
    assert not (project_root / ".cursor").exists()
    assert ".cursor" not in (project_root / "AGENTS.md").read_text(encoding="utf-8")


def test_existing_install_is_kept_without_force_and_other_targets_continue(project_root: Path) -> None:
    custom = project_root / ".claude/skills/migrate-di/SKILL.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("mine\n", encoding="utf-8")
    result = _invoke("migrate-di")
    assert result.exit_code == 0  # type: ignore[attr-defined]
    assert "--force" in result.output  # type: ignore[attr-defined]
    assert custom.read_text(encoding="utf-8") == "mine\n"
    assert (project_root / ".cursor/skills/migrate-di/SKILL.md").is_file()


def test_force_overwrites(project_root: Path) -> None:
    custom = project_root / ".claude/skills/migrate-di/SKILL.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("mine\n", encoding="utf-8")
    assert _invoke("migrate-di", "--target", "claude", "--force").exit_code == 0  # type: ignore[attr-defined]
    assert custom.read_text(encoding="utf-8") != "mine\n"


def test_agents_md_is_preserved_and_idempotent(project_root: Path) -> None:
    agents = project_root / "AGENTS.md"
    agents.write_text("# Team notes\n\nKeep me.\n", encoding="utf-8")
    _invoke("migrate-di", "--target", "agents")
    _invoke("migrate-di", "--target", "agents", "--force")
    content = agents.read_text(encoding="utf-8")
    assert content.startswith("# Team notes\n\nKeep me.\n")
    assert content.count("- `migrate-di`:") == 1


def test_unknown_target_is_a_usage_error(project_root: Path) -> None:
    assert _invoke("migrate-di", "--target", "vim").exit_code == 2  # type: ignore[attr-defined]
