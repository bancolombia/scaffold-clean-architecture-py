"""Hygiene gates: no Spec Kit ID references, no banner comment lines."""

from __future__ import annotations

import re
from pathlib import Path

_SRC = Path(__file__).parent.parent / "src" / "scaffold_ca_python"
_ID_PATTERN = re.compile(r"\b(T0\d{2}|FR-\d{3}|US-?\d|R-\d{2})\b|Phase \d")
_BANNER_PREFIX = "# ---"


def _source_files() -> list[Path]:
    return [p for p in sorted(_SRC.rglob("*.py")) if "templates" not in p.parts]


def test_no_spec_kit_ids() -> None:
    matches: list[str] = []
    for path in _source_files():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if _ID_PATTERN.search(line):
                rel = path.relative_to(_SRC.parent.parent)
                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
    assert not matches, "Spec Kit IDs found in source:\n" + "\n".join(matches)


def test_no_banner_comment_lines() -> None:
    matches: list[str] = []
    for path in _source_files():
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if line.lstrip().startswith(_BANNER_PREFIX):
                rel = path.relative_to(_SRC.parent.parent)
                matches.append(f"{rel}:{lineno}: {line.rstrip()}")
    assert not matches, "Banner comment lines found in source:\n" + "\n".join(matches)
