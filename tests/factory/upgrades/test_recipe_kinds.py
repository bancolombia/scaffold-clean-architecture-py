"""Pending kinds align with skill recipes."""

from __future__ import annotations

from pathlib import Path

PENDING_KINDS = {
    "resource_provider",
    "configuration_provider",
    "selector_provider",
    "callable_provider",
    "nested_container",
    "override_in_test",
    "usecase_uses_helper",
    "composition_root_modified",
    "factory_provider",
}

RECIPES = Path(__file__).resolve().parents[3] / "src/scaffold_ca_python/skills/migrate-di/references/recipes.md"


def test_recipes_cover_pending_kinds() -> None:
    text = RECIPES.read_text(encoding="utf-8")
    for kind in PENDING_KINDS:
        if kind == "factory_provider":
            continue  # mapped to callable_provider in user docs
        assert kind in text, f"missing recipe for {kind}"


def test_contract_pending_enum_subset() -> None:
    contract = Path(__file__).resolve().parents[3] / "specs/029-upgrade-framework/contracts/pending-items.md"
    body = contract.read_text(encoding="utf-8")
    for kind in PENDING_KINDS - {"factory_provider"}:
        assert kind in body
