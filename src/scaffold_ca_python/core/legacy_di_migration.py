"""Pyproject and source helpers for legacy DI → wireup migration."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from scaffold_ca_python.core.pyproject_writer import _name_prefix

_WIREUP_DEP = "wireup==2.13.0"


def pyproject_has_package(project_root: Path, bare_name: str) -> bool:
    data = _load(project_root)
    deps: list[str] = data.get("project", {}).get("dependencies", [])
    return _name_prefix(bare_name) in {_name_prefix(d) for d in deps}


def _load(project_root: Path) -> dict[str, Any]:
    with (project_root / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def _save(project_root: Path, data: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    with (project_root / "pyproject.toml").open("wb") as fh:
        tomli_w.dump(data, fh)


def migrate_pyproject_to_wireup(project_root: Path, scaffold_version: str, *, dry_run: bool) -> bool:
    """Swap dependency-injector for wireup and set tooling keys. Returns True if changes queued."""
    data = _load(project_root)
    project = data.setdefault("project", {})
    deps: list[str] = list(project.get("dependencies", []))
    changed = False
    new_deps: list[str] = []
    for dep in deps:
        if _name_prefix(dep) == "dependency-injector":
            new_deps.append(_WIREUP_DEP)
            changed = True
        else:
            new_deps.append(dep)
    if _name_prefix(_WIREUP_DEP) not in {_name_prefix(d) for d in new_deps}:
        new_deps.append(_WIREUP_DEP)
        changed = True
    project["dependencies"] = new_deps

    tool = data.setdefault("tool", {})
    sca = tool.setdefault("scaffold-ca-python", {})
    if sca.get("scaffold_version") != scaffold_version:
        sca["scaffold_version"] = scaffold_version
        changed = True

    ruff = tool.setdefault("ruff", {})
    lint = ruff.setdefault("lint", {})
    select: list[str] = list(lint.get("select", []))
    if "ASYNC" not in select:
        select.append("ASYNC")
        lint["select"] = select
        changed = True
    ignore: list[str] = list(lint.get("ignore", []))
    if "TC" not in ignore:
        ignore.append("TC")
        lint["ignore"] = ignore
        changed = True

    pytest = tool.setdefault("pytest.ini_options", {})
    if pytest.get("asyncio_mode") != "auto":
        pytest["asyncio_mode"] = "auto"
        changed = True

    if changed:
        _save(project_root, data, dry_run=dry_run)
    return changed


def write_scaffold_version(project_root: Path, version: str, *, dry_run: bool) -> bool:
    data = _load(project_root)
    sca = data.setdefault("tool", {}).setdefault("scaffold-ca-python", {})
    if sca.get("scaffold_version") == version:
        return False
    sca["scaffold_version"] = version
    _save(project_root, data, dry_run=dry_run)
    return True


def find_container_files(project_root: Path, python_package: str) -> list[Path]:
    config = project_root / "src" / python_package / "application" / "config"
    if not config.is_dir():
        return []
    return sorted(config.glob("*_container.py"))


def rewrite_provide_to_injected(content: str) -> tuple[str, int]:
    """Naive Provide → Injected for entry-point parameters."""
    count = 0

    def repl_depends(m: re.Match[str]) -> str:
        nonlocal count
        count += 1
        return f": Injected[{m.group(1)}]"

    new_content, n1 = re.subn(
        r":\s*\w+\s*=\s*Depends\(\s*Provide\[([^\]]+)\]\s*\)",
        repl_depends,
        content,
    )
    new_content, n2 = re.subn(r"=\s*Provide\[([^\]]+)\]", r"= Injected[\1]", new_content)
    return new_content, n1 + n2


def scan_container_pending(container_path: Path) -> list[tuple[str, int, str]]:
    """Return pending (kind, line, guide_section) tuples from container source."""
    pending: list[tuple[str, int, str]] = []
    text = container_path.read_text(encoding="utf-8")
    patterns = [
        (r"providers\.Resource", "resource_provider", "providers-resource"),
        (r"providers\.Configuration", "configuration_provider", "providers-configuration"),
        (r"providers\.Selector", "selector_provider", "providers-selector"),
        (r"providers\.Callable", "callable_provider", "providers-callable"),
        (r"providers\.Container", "nested_container", "nested-container"),
    ]
    for i, line in enumerate(text.splitlines(), start=1):
        for regex, kind, section in patterns:
            if re.search(regex, line):
                pending.append((kind, i, section))
    return pending
