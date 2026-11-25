"""Every pending kind has a recipe, a guide anchor and a contract row (and nothing else does)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scaffold_ca_python.factory.upgrades.report import AUTOMATED_KINDS, PENDING_KINDS, AppliedItem, PendingItem

_ROOT = Path(__file__).resolve().parents[3]
_RECIPES = _ROOT / "src/scaffold_ca_python/skills/migrate-di/references/recipes.md"
_GUIDE = _ROOT / "docs/migration/dependency-injector-to-wireup.md"
_CONTRACT = _ROOT / "specs/029-upgrade-framework/contracts/pending-items.md"


def test_recipes_have_exactly_one_heading_per_pending_kind() -> None:
    headings = re.findall(r"^## (\S+)$", _RECIPES.read_text(encoding="utf-8"), re.MULTILINE)
    assert sorted(headings) == sorted(PENDING_KINDS)


def test_guide_has_an_anchor_and_heading_per_pending_kind() -> None:
    guide = _GUIDE.read_text(encoding="utf-8")
    anchors = re.findall(r'<a id="([\w-]+)"></a>\n### `(\w+)`', guide)
    assert dict((kind, anchor) for anchor, kind in anchors) == PENDING_KINDS


def test_contract_lists_every_kind() -> None:
    contract = _CONTRACT.read_text(encoding="utf-8")
    for kind, section in PENDING_KINDS.items():
        assert f"| `{kind}` | `{section}` |" in contract
    for kind in AUTOMATED_KINDS:
        assert f"| `{kind}` |" in contract


def test_unknown_kinds_are_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown pending kind"):
        PendingItem(kind="factory_provider", file="x.py", line=1)
    with pytest.raises(ValueError, match="Unknown automated kind"):
        AppliedItem(kind="something_else", file="x.py")
