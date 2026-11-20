"""install-skill: copy packaged agent skills into a target project."""

from __future__ import annotations

import shutil
from pathlib import Path

import typer

from scaffold_ca_python.commands._shared import console, fail, require_project_root

_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills"

_TARGETS = {
    "claude": ".claude/skills",
    "cursor": ".cursor/skills",
    "agents": ".agents/skills",
}


def _install_one(project_root: Path, skill: str, target_key: str, *, force: bool) -> None:
    src = _SKILL_ROOT / skill
    if not src.is_dir():
        fail(f"Skill '{skill}' is not packaged with this scaffolder.")
    rel = _TARGETS[target_key]
    dest = project_root / rel / skill
    if dest.exists() and not force:
        console.print(f"[yellow]⚠[/yellow] Skill already installed at {dest}. Use --force to overwrite.")
        raise typer.Exit(0)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    console.print(f"[green]✓[/green] Installed {skill} → {dest}")


def _append_agents_md(project_root: Path, skill: str) -> None:
    agents = project_root / "AGENTS.md"
    line = f"- Skill: `{skill}` — see `.cursor/skills/{skill}/SKILL.md` (or harness-specific path).\n"
    if agents.exists():
        content = agents.read_text(encoding="utf-8")
        if skill in content:
            return
        agents.write_text(content.rstrip() + "\n" + line, encoding="utf-8")
    else:
        agents.write_text(f"# Agent skills\n\n{line}", encoding="utf-8")


def register(app: typer.Typer) -> None:
    def install_skill(
        skill: str,
        target: str = "all",
        force: bool = False,
    ) -> None:
        project_root = require_project_root()
        keys = list(_TARGETS) if target == "all" else [target]
        if any(k not in _TARGETS for k in keys):
            fail(f"Unknown target {target!r}. Use claude, cursor, agents, or all.")
        for key in keys:
            _install_one(project_root, skill, key, force=force)
        _append_agents_md(project_root, skill)

    app.command(
        "install-skill",
        help="Copy a packaged migration or helper skill into the target project.",
    )(install_skill)
