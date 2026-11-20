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

**Decision**: The DI migration action writes `scaffold_version` (installed version) inside its single pyproject edit, because adopting wireup is what the key marks (FR-020 of 028). The runner only *aligns* a key that already exists: after a non-dry-run with applied items, if the declared version differs from the installed one it rewrites it and reports `scaffold_version_updated`. So the key has one writer per run: the DI action on legacy projects, the runner on already-wireup projects touched by future actions. If declared version > installed, warn and skip all actions (H4).

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

**Decision**: `ModuleBuilder.preview_diffs()` renders a `difflib.unified_diff` per queued operation with project-relative `a/`/`b/` paths (H5, FR-002). `FileWriter` keeps its path-only dry-run, so every other command's preview is unchanged; insert/append previews reuse the same pure helpers (`insert_after_text`, `append_text`) the writer applies.

**Formatting**: the runner returns the paths it wrote and `update_project` formats only those (`auto_format_project(root, paths)`), so the applied tree equals the reviewed diff plus formatting of written files.

**Limitation (M1)**: the runner persists after each action; in dry-run, action N+1 does not see N's planned writes—documented in quickstart.

---

## R8 — libcst import

**Decision**: libcst code lives in `factory/upgrades/actions/di_wireup/codemod.py` and is imported inside `UpgradeDependencyInjectorToWireup.up()` only; `applies()` uses plain regex/TOML checks. `tests/factory/upgrades/test_lazy_libcst.py` asserts that importing the CLI and the registry does not load libcst (L2).

---

## R9 — Skill installation

**Decision**: Separate `scaffold install-skill migrate-di` command (L1); not a flag on `up`.

---

## R10 — Fixture strategy

**Decision**: `tests/fixtures/legacy_050_project/` is generated with 0.5.0 (`ca`, `gm book`, `guc get_book`, `gda generic book_store`, `gep restapi`) plus the hand wiring a 0.5.0 developer writes (Singleton bindings, `Depends(Provide[...])` endpoint, a `providers.Resource`); its own 18 tests pass under dependency-injector. `upgrade_di_golden/` is the expected `up` output; `upgrade_di_resolution/` is the manual resolution of the pending `resource_provider`. Golden + resolution is the reference for SC-001, and the e2e test proves it passes ruff, mypy --strict, pytest and `vs` (L3).

---

## R11 — Composition root fingerprint

**Decision**: The 0.5.0 restapi `app.py` and `test_app.py` templates are shipped under `templates/upgrades/dependency_injector_to_wireup/`, rendered with the project's name and package, and compared by SHA-256 with the file on disk (clarification session 2026-11-20). A match is replaced with the 1.0.0 template; anything else that uses the legacy container is pending.

**Alternatives considered**: Precomputed digests (cannot account for project metadata); normalized comparison (accepts edited files silently); always pending (reduces automation below SC-001).

---

## R13 — Pre-scaffold projects (US4)

**Decision**: Adoption is explicit: the user adds `[tool.scaffold-ca-python]` (the error prints the block, with `name` derived from the single `src/` package). `scaffold up` does not write the section itself, because it cannot confirm that an arbitrary repository follows the layout. Naming variants (`use_cases/`, `gateway/`) are recognized by the codemod; configuration passed by value is **not** converted automatically. Choosing settings classes, env prefixes and field names is a design decision, so it is delegated to the skill (`references/pre-scaffold.md`).

**Evidence**: dry-run on copies of two pre-scaffold services (MCP server and A2A agent). After adoption, 10/26 and 4/25 items were automated; most of the pending items were `provider_arguments` with `settings.X` values (7–8 each), followed by resources, custom composition roots and container tests.

**Alternatives considered**: an `up --adopt` flag (silently accepts non-conforming repos); heuristic settings generation (produces classes the team would redesign).

---

## R12 — Injection rewrite safety

**Decision**: A `Provide` parameter is converted to `Injected[T]` only when it is annotated and no earlier positional parameter keeps a default; otherwise it is left as is and reported `injection_unresolved`. Reordering parameters was rejected because it changes positional call semantics.