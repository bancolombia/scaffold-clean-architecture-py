"""install-skill: copy packaged agent skills into a target project."""

from __future__ import annotations

import shutil
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from scaffold_ca_python.commands._shared import console, fail, require_project_root

_SKILL_ROOT = Path(__file__).resolve().parent.parent / "skills"
_AGENTS_MD_MARKER = "<!-- scaffold-ca-python skills -->"


class SkillTarget(StrEnum):
    claude = "claude"
    cursor = "cursor"
    agents = "agents"
    all = "all"


_TARGET_DIRS = {
    SkillTarget.claude: Path(".claude/skills"),
    SkillTarget.cursor: Path(".cursor/skills"),
    SkillTarget.agents: Path(".agents/skills"),
}


def packaged_skills() -> list[str]:
    """Names of skills shipped in the wheel (directories containing ``SKILL.md``)."""
    return sorted(p.name for p in _SKILL_ROOT.iterdir() if (p / "SKILL.md").is_file())


def _install_one(project_root: Path, skill: str, target_dir: Path, *, force: bool) -> Path | None:
    dest = project_root / target_dir / skill
    if dest.exists() and not force:
        console.print(f"[yellow]⚠[/yellow] {dest.relative_to(project_root)} already exists; use --force to overwrite.")
        return None
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(_SKILL_ROOT / skill, dest)
    console.print(f"[green]✓[/green] Installed {skill} → {dest.relative_to(project_root)}")
    return dest


def _update_agents_md(project_root: Path, skill: str, installed: list[Path]) -> None:
    agents = project_root / "AGENTS.md"
    paths = ", ".join(f"`{(p / 'SKILL.md').relative_to(project_root).as_posix()}`" for p in installed)
    line = f"- `{skill}`: {paths}\n"
    content = agents.read_text(encoding="utf-8") if agents.exists() else "# Agent instructions\n"
    if line in content:
        return
    if _AGENTS_MD_MARKER not in content:
        content = content.rstrip("\n") + f"\n\n## Skills\n\n{_AGENTS_MD_MARKER}\n"
    content = content.replace(f"{_AGENTS_MD_MARKER}\n", f"{_AGENTS_MD_MARKER}\n{line}", 1)
    agents.write_text(content, encoding="utf-8")


def register(app: typer.Typer) -> None:
    def install_skill(
        skill: Annotated[str, typer.Argument(help="Skill name, e.g. migrate-di.")],
        target: Annotated[SkillTarget, typer.Option("--target", help="Harness directory to populate.")] = (
            SkillTarget.all
        ),
        force: Annotated[bool, typer.Option("--force", help="Overwrite an existing installation.")] = False,
    ) -> None:
        available = packaged_skills()
        if skill not in available:
            fail(f"Unknown skill {skill!r}.", hint=f"Available skills: {', '.join(available)}.")
        project_root = require_project_root()
        dirs = list(_TARGET_DIRS.values()) if target == SkillTarget.all else [_TARGET_DIRS[target]]
        installed = [d for d in (_install_one(project_root, skill, t, force=force) for t in dirs) if d is not None]
        if installed:
            _update_agents_md(project_root, skill, installed)

    app.command(
        "install-skill",
        help="Copy a packaged agent skill (e.g. migrate-di) into the project's harness directories.",
        epilog="Example:\n\n  * scaffold install-skill migrate-di --target claude",
    )(install_skill)
