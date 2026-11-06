"""Hygiene gates: no Spec Kit ID references, no banner comment lines."""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_SRC = _ROOT / "src" / "scaffold_ca_python"
_ID_PATTERN = re.compile(r"\b(T\d{3}|FR-\d{3}|SC-\d{3}|US-?\d|R-\d{2}|D\d{1,2}|DEF-[A-Z]+-\d+)\b|Phase \d")
_BANNER_PREFIX = "# ---"


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
