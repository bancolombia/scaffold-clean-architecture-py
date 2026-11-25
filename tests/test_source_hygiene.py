"""Hygiene gates: no Spec Kit IDs, no banner comments, slow `uv` tests confined to tests/e2e/."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_SRC = _ROOT / "src" / "scaffold_ca_python"
_ID_PATTERN = re.compile(r"\b(T\d{3}|FR-\d{3}|SC-\d{3}|US-?\d|R-\d{2}|D\d{1,2}|DEF-[A-Z]+-\d+)\b|Phase \d")
_BANNER_PREFIX = "# ---"
_E2E_DIR = _ROOT / "tests" / "e2e"
_UV_COMMAND = re.compile(r"subprocess\.(run|Popen|call|check_call|check_output)\(\s*[\[(]\s*[\"']uv[\"']")
_E2E_MARK = re.compile(r"^pytestmark\s*=.*\bpytest\.mark\.e2e\b", re.MULTILINE)


def _source_files() -> list[Path]:
    return [p for p in sorted(_SRC.rglob("*.py")) if "templates" not in p.parts]


def test_no_spec_kit_ids_in_source() -> None:
    matches: list[str] = []
    for path in _source_files():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if _ID_PATTERN.search(line):
                rel = path.relative_to(_ROOT)
                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
    assert not matches, "Spec Kit IDs found in source:\n" + "\n".join(matches)


def test_no_spec_kit_ids_in_tests_and_templates() -> None:
    matches: list[str] = []
    paths = list((_ROOT / "tests").rglob("*.py")) + list((_SRC / "templates").rglob("*.jinja2"))
    for path in paths:
        if path.name == "test_source_hygiene.py":
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _ID_PATTERN.search(line):
                rel = path.relative_to(_ROOT)
                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
    assert not matches, "Spec Kit IDs found:\n" + "\n".join(matches[:50])


def test_no_banner_comment_lines() -> None:
    matches: list[str] = []
    for path in _source_files():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if line.lstrip().startswith(_BANNER_PREFIX):
                rel = path.relative_to(_ROOT)
                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
    assert not matches, "Banner comment lines found in source:\n" + "\n".join(matches)


def test_real_uv_commands_only_in_e2e() -> None:
    matches: list[str] = []
    for path in sorted((_ROOT / "tests").rglob("*.py")):
        if _E2E_DIR in path.parents:
            continue
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if _UV_COMMAND.search(line):
                matches.append(f"{path.relative_to(_ROOT)}:{lineno}: {line.strip()}")
    assert not matches, "Real `uv` invocations belong in tests/e2e/ (slow):\n" + "\n".join(matches)


def test_e2e_modules_are_marked() -> None:
    unmarked = [
        str(path.relative_to(_ROOT))
        for path in sorted(_E2E_DIR.glob("test_*.py"))
        if not _E2E_MARK.search(path.read_text(encoding="utf-8"))
    ]
    assert not unmarked, "Missing `pytestmark = pytest.mark.e2e`:\n" + "\n".join(unmarked)
