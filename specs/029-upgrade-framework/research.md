# Research: Upgrade framework in `scaffold up`

**Date**: 2026-11-20  
**Spec**: [spec.md](spec.md)

---

## R1 — Content-based action selection vs version-based filtering

**Decision**: Each `UpgradeAction` implements `applies(builder) -> bool` using project **content** (imports, dependencies, file patterns). Registry order is a single explicit list `UPGRADE_ACTIONS`; a test asserts module name date segments are monotonic.

**Rationale**: Writing `scaffold_version` on first migration (H1) hides further pending detection if later runs filter only by version. Content markers (`dependency-injector`, `*_container.py`, missing `wiring.py`) remain until the tree is wireup-clean.

**Alternatives rejected**:
- `min_version` / `max_version` / `date` fields on the ABC (H3): fragile with editable installs (`0.0.0+unknown`) and requires undeclared `packaging`.
- Running filters only on legacy absence of `scaffold_version`: breaks idempotent reporting of pending items.

---

## R2 — Order of dependency refresh vs codemods

**Decision**: Upgrade actions → `uv lock --upgrade` → `uv sync`.

**Rationale**: Running lock first (current `up`) can bump `dependency-injector` before the action removes it, producing a misleading lockfile and ambiguous failure attribution (H2).

---

## R3 — `scaffold_version` lifecycle

**Decision**: The DI migration action writes `scaffold_version` when it applies automated edits. After a successful non-dry-run with any applied items, the runner sets `scaffold_version` to the **installed** scaffolder version. If declared version > installed, warn and skip all actions (H4).

**Rationale**: Aligns with FR-020 legacy detection in 028; wireup adoption is explicit in pyproject.

---

## R4 — Clean tree policy

**Decision**: Require clean tree only when at least one action applies and the run is not dry-run; `--allow-dirty` bypasses (M4).

**Rationale**: Routine `up` on wireup projects unaffected; idempotent second run on migrated project does not fail on dirty tree if no actions apply.

---

## R5 — Reporting and exit codes

**Decision**: Exit `1` for any failure; exit `0` when automated steps succeed even if pending items remain. `--report json` on stdout only; Rich and `uv` on stderr (M2, M3).

---

## R6 — `UpgradeAction` location and pattern

**Decision**: ABC in `factory/upgrades/` with ClassVar `name` and `description`, methods `applies` and `up`, mirroring `EntryPointFactory` (M5). Concrete actions under `factory/upgrades/actions/` with dated module names.

**Not used**: `min_version`, `max_version`, `date` on the ABC; separate `migrate-di` command.

---

## R7 — Dry-run diffs

**Decision**: Extend `FileWriter` / `ModuleBuilder` dry-run to accumulate before/after text and emit `difflib.unified_diff` (H5 FR-002). Path-only dry-run remains for non-upgrade commands.

**Limitation (M1)**: Runner calls `persist_and_format` after each action; in dry-run, action N+1 does not see N's in-memory writes on disk—document in quickstart.

---

## R8 — libcst import

**Decision**: Import `libcst` inside the DI action module only (L2).

---

## R9 — Skill installation

**Decision**: Separate `scaffold install-skill migrate-di` command (L1); not a flag on `up`.

---

## R10 — Fixture strategy

**Decision**: One committed static tree from `uvx scaffold-ca-python==0.5.0` (L3); golden tests for `up` and JSON report.

---

## R11 — Composition root fingerprint

**Decision**: SHA-256 of file bytes compared to precomputed digest from 0.5.0 render for the same package metadata (clarification session 2026-11-20).

**Alternatives considered**: Byte-for-byte only (brittle on line endings); always pending (reduces automation below SC-001).