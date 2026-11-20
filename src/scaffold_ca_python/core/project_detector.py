"""project_detector: locate and read project metadata."""

from __future__ import annotations

import tomllib
from collections.abc import Iterator
from pathlib import Path

from scaffold_ca_python.core.errors import ScaffoldError
from scaffold_ca_python.models.context import ProjectContext

_CA_MARKERS: frozenset[str] = frozenset({"domain", "infrastructure", "application"})
_SCAFFOLD_SECTION = "scaffold-ca-python"


class MissingScaffoldSectionError(ScaffoldError):
    """A ``pyproject.toml`` exists but lacks ``[tool.scaffold-ca-python]`` (project predates the scaffolder)."""

    def __init__(self, pyproject: Path) -> None:
        self.pyproject = pyproject
        self.suggested_name = _suggested_name(pyproject)
        super().__init__(
            f"{pyproject} has no [tool.scaffold-ca-python] section.\n"
            "If this is a Clean Architecture project, add:\n\n"
            f'[tool.scaffold-ca-python]\nname = "{self.suggested_name}"\n\n'
            "then run `scaffold up --dry-run` to migrate it "
            "(see docs/migration/dependency-injector-to-wireup.md)."
        )


def _load_toml(pyproject: Path) -> dict[str, object] | None:
    try:
        with pyproject.open("rb") as fh:
            return tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError):
        return None


def _suggested_name(pyproject: Path) -> str:
    """Kebab-case name whose snake form matches the single package under ``src/``."""
    src = pyproject.parent / "src"
    packages = (
        [p.name for p in src.iterdir() if p.is_dir() and (p / "__init__.py").is_file() and p.name != "tests"]
        if src.is_dir()
        else []
    )
    if len(packages) == 1:
        return packages[0].replace("_", "-")
    project = (_load_toml(pyproject) or {}).get("project", {})
    name = project.get("name") if isinstance(project, dict) else None
    return str(name) if name else pyproject.parent.name


def _nearest_pyproject(start: Path) -> Path | None:
    return next((d / "pyproject.toml" for d in _iter_parents(start) if (d / "pyproject.toml").is_file()), None)


def find_project_root(cwd: Path | None = None) -> Path:
    """Walk upward from *cwd* to locate the project root.

    Strategy:
    1. Look for a ``pyproject.toml`` that contains ``[tool.scaffold-ca-python]``.
    2. If not found, fall back to a directory whose children include the three
       canonical CA layout directories (``domain/``, ``infrastructure/``,
       ``application/``).

    Raises
    ------
    ScaffoldError
        When neither strategy finds a suitable root before reaching the
        filesystem boundary.
    """
    current = (cwd or Path.cwd()).resolve()

    # Strategy 1: pyproject.toml with [tool.scaffold-ca-python]
    candidate: Path | None = None
    for directory in _iter_parents(current):
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            try:
                with pyproject.open("rb") as fh:
                    data = tomllib.load(fh)
                if _SCAFFOLD_SECTION in data.get("tool", {}):
                    candidate = directory
                    break
            except Exception:  # malformed TOML — skip silently
                pass

    if candidate is not None:
        return candidate

    # Strategy 2: canonical CA directory layout
    nearest = _nearest_pyproject(current)
    for directory in _iter_parents(current):
        children = {p.name for p in directory.iterdir() if p.is_dir()}
        if _CA_MARKERS.issubset(children):
            if nearest is not None and nearest.parent != directory and directory.is_relative_to(nearest.parent):
                # src/<pkg>/ of a project whose pyproject.toml lacks the section.
                raise MissingScaffoldSectionError(nearest)
            return directory

    if nearest is not None:
        raise MissingScaffoldSectionError(nearest)

    raise ScaffoldError(
        "Could not find a scaffold-ca-python project root. "
        "Ensure you are inside a project directory or run 'scaffold generate-project' first. "
        "Hint: a valid project root has either [tool.scaffold-ca-python] in pyproject.toml "
        "or the canonical CA directory layout (domain/, infrastructure/, application/)."
    )


def load_project_context(root: Path) -> ProjectContext:
    """Read [tool.scaffold-ca-python] fields from pyproject.toml, falling back to root.name.

    If the ``scaffold_version`` key is absent the project is treated as legacy
    (generated with scaffold-ca-python ≤ 0.5.0).
    """
    pyproject = root / "pyproject.toml"
    with pyproject.open("rb") as fh:
        data = tomllib.load(fh)
    section = data.get("tool", {}).get("scaffold-ca-python", {})
    scaffold_version: str | None = section.get("scaffold_version")
    return ProjectContext(
        name=section.get("name", root.name),
        scaffold_version=scaffold_version,
        project_root=root,
    )


def resolve_tests_root(project_root: Path) -> Path:
    """Return the tests root for a project, probing for src-layout vs root-layout.

    Resolution order:
    1. ``project_root/src/tests/`` if it already exists (src-layout, post-feature).
    2. ``project_root/tests/`` if it already exists (root-layout, pre-feature).
    3. ``project_root/src/tests/`` as the default for new projects.
    """
    src_tests = project_root / "src" / "tests"
    if src_tests.exists():
        return src_tests
    root_tests = project_root / "tests"
    if root_tests.exists():
        return root_tests
    return src_tests


def _iter_parents(start: Path) -> Iterator[Path]:
    """Yield *start* and each parent up to (and including) the filesystem root."""
    current = start
    while True:
        yield current
        parent = current.parent
        if parent == current:
            break
        current = parent
