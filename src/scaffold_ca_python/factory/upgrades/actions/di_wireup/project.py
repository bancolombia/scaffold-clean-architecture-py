"""Project-level helpers for the dependency-injector → wireup action (no libcst)."""

from __future__ import annotations

import hashlib
import io
import re
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.pyproject_writer import _name_prefix
from scaffold_ca_python.factory.dependencies import MYPY, WIREUP

LEGACY_RESTAPI_APP = "upgrades/dependency_injector_to_wireup/restapi_app_0_5_0.py.jinja2"
RESTAPI_APP = "entry_point/restapi/app.py.jinja2"
LEGACY_RESTAPI_TEST_APP = "upgrades/dependency_injector_to_wireup/restapi_test_app_0_5_0.py.jinja2"
RESTAPI_TEST_APP = "entry_point/restapi/test_app.py.jinja2"

_USECASE_MODULE = re.compile(r"\.domain\.(?:usecases?|use_cases?)(?:\.|$)")
_DI_IMPORT = re.compile(r"^[ \t]*(?:from|import)[ \t]+dependency_injector\b", re.MULTILINE)
_CONTAINER_IMPORT = re.compile(r"^[ \t]*from[ \t]+[\w.]+\.application\.config\.container[ \t]+import\b", re.MULTILINE)


def is_usecase_module(module: str) -> bool:
    """True for ``domain.usecase`` and the ``usecases`` / ``use_case`` / ``use_cases`` variants."""
    return bool(_USECASE_MODULE.search(module))


def container_files(src_pkg: Path) -> list[Path]:
    """Return the 0.5.0 declarative container modules under ``application/config``."""
    config = src_pkg / "application" / "config"
    if not config.is_dir():
        return []
    files = sorted(config.glob("*_container.py"))
    root = config / "container.py"
    return [root, *files] if root.is_file() else files


def uses_legacy_di(text: str) -> bool:
    """True when *text* imports ``dependency_injector`` or the legacy root container."""
    return bool(_DI_IMPORT.search(text) or _CONTAINER_IMPORT.search(text))


def first_legacy_di_line(text: str) -> int:
    starts = [match.start() for pattern in (_DI_IMPORT, _CONTAINER_IMPORT) if (match := pattern.search(text))]
    return text.count("\n", 0, min(starts)) + 1 if starts else 1


def python_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.py") if p.is_file() and ".venv" not in p.parts)


def _load(project_root: Path) -> dict[str, Any]:
    with (project_root / "pyproject.toml").open("rb") as fh:
        return tomllib.load(fh)


def depends_on_dependency_injector(project_root: Path) -> bool:
    deps: list[str] = _load(project_root).get("project", {}).get("dependencies", [])
    return "dependency-injector" in {_name_prefix(d) for d in deps}


def _ensure_in(values: list[str], item: str) -> bool:
    if item in values:
        return False
    values.append(item)
    return True


def migrated_pyproject(project_root: Path, scaffold_version: str) -> str | None:
    """Return the migrated ``pyproject.toml`` text, or None when nothing changes."""
    data = _load(project_root)
    changed = False

    project = data.setdefault("project", {})
    deps = [d for d in project.get("dependencies", []) if _name_prefix(d) != "dependency-injector"]
    changed |= len(deps) != len(project.get("dependencies", []))
    if _name_prefix(WIREUP) not in {_name_prefix(d) for d in deps}:
        deps.insert(0, WIREUP)
        changed = True
    project["dependencies"] = deps

    dev: list[object] = data.setdefault("dependency-groups", {}).setdefault("dev", [])
    if _name_prefix(MYPY) not in {_name_prefix(d) for d in dev if isinstance(d, str)}:
        dev.insert(0, MYPY)
        changed = True

    tool = data.setdefault("tool", {})
    sca = tool.setdefault("scaffold-ca-python", {})
    if sca.get("scaffold_version") != scaffold_version:
        sca["scaffold_version"] = scaffold_version
        changed = True

    lint = tool.setdefault("ruff", {}).setdefault("lint", {})
    changed |= _ensure_in(lint.setdefault("select", []), "ASYNC")
    changed |= _ensure_in(lint.setdefault("ignore", []), "TC")

    ini = tool.setdefault("pytest", {}).setdefault("ini_options", {})
    if ini.get("asyncio_mode") != "auto":
        ini["asyncio_mode"] = "auto"
        changed = True

    if not changed:
        return None
    buffer = io.BytesIO()
    tomli_w.dump(data, buffer)
    return buffer.getvalue().decode("utf-8")


def render_context(builder: ModuleBuilder) -> dict[str, object]:
    base = builder.base_context()
    return {**base, "project": builder.project_ctx.model_dump(), "routes": []}


def matches_legacy_render(builder: ModuleBuilder, path: Path, legacy_template: str) -> bool:
    """True when *path* is byte-identical (SHA-256) to *legacy_template* rendered for this project by 0.5.0."""
    if not path.is_file():
        return False
    expected = builder.render(legacy_template, render_context(builder)).encode("utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest() == hashlib.sha256(expected).hexdigest()
