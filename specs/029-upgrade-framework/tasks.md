---

description: "Task list for Upgrade framework in scaffold up"

---

# Tasks: Upgrade framework in `scaffold up`

**Input**: Design documents from `/specs/029-upgrade-framework/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required (Constitution II/V; SC-001–SC-003).

**Organization**: Phases by user story; spec-028 doc fixes grouped in Phase 2.

---

## Phase 1: Setup

- [x] T001 Confirm branch `feature/029-upgrade-framework` and baseline `uv run pytest` (record pass count).
- [x] T002 Add `libcst` to scaffolder dependencies in `pyproject.toml` (runtime or optional extra per R8—default runtime for migrate action).
- [x] T003 [P] Generate static fixture `tests/fixtures/legacy_050_project/` via `uvx scaffold-ca-python==0.5.0` once; commit tree + README for regeneration (L3). *(Redone in T040: the first fixture was an empty `ca` output.)*

---

## Phase 2: Spec 028 alignment (H6, H7, M6) — docs only

- [x] T004 Update FR-020 in `specs/028-wireup-di/spec.md`: exempt `up` with `ca` and `vs`; link to `specs/029-upgrade-framework/`; note «Superseded in part by spec 029»; replace `migrate-di` wording with `scaffold up` / `install-skill migrate-di`.
- [x] T005 Update `specs/028-wireup-di/contracts/generated-files.md` § Legacy Projects: remove `up` from refused commands; same exemption note; point migration to 029.
- [x] T006 [P] Rewrite all 22 `docs/spec-029-migrate-di` references under `specs/028-wireup-di/` to `specs/029-upgrade-framework/` (verify with `git grep -c spec-029 specs/028-wireup-di` → 0 for old path). *(10 links pointed to a non-existent `README.md`; fixed in T050.)*
- [x] T007 Delete obsolete `specs/028-wireup-di/contracts/migrate-di.md`; replace cross-links with `specs/029-upgrade-framework/contracts/`.
- [x] T008 Change `_LEGACY_MIGRATION_HINT` in `src/scaffold_ca_python/commands/_shared.py` to instruct `scaffold up` (implementation with US1).

---

## Phase 3: Foundational — upgrade framework (US2)

**Goal**: Registry, ABC, runner skeleton; no DI codemod yet.

### Tests first

- [x] T009 [P] Add `tests/factory/upgrades/test_registry_order.py`: `UPGRADE_ACTIONS` module name dates are non-decreasing (H3).
- [x] T010 [P] Add `tests/factory/upgrades/test_runner.py`: clean-tree rule incl. non-git trees (M4), newer `scaffold_version` skips actions (H4), registry order, idempotent no-op action, failing action.

### Implementation

- [x] T011 [P] Create `factory/upgrades/base.py` — `UpgradeAction` ABC with ClassVar `name`, `description`, `applies`, `up` (no version fields) (M5).
- [x] T012 Create `factory/upgrades/__init__.py` — `UPGRADE_ACTIONS` list and typed registry export.
- [x] T013 Create `factory/upgrades/runner.py` — `UpgradeRunner.run()`: iterate actions, persist after each (M1), return written paths for formatting, aggregate `UpgradeReport`.
- [x] T014 Add stub action `upgrade_2026_11_20_dependency_injector_to_wireup.py` returning empty result until US1 fills it.
- [x] T015 T009–T010 green.

**Checkpoint**: Runner callable from tests with stub action.

---

## Phase 4: User Story 1 — DI migration (P1) MVP

**Goal**: Full DI action + `up` integration + diffs + JSON report.

### Tests first

- [x] T016 [US1] Integration test: `scaffold up --dry-run` on `legacy_050_project` → whole-tree snapshot unchanged; stdout/stderr contract (`tests/commands/test_update_project_upgrades.py`).
- [x] T017 [US1] Golden test: apply `up` on fixture → equals `upgrade_di_golden/`; ≥70% of required line edits automated vs golden + `upgrade_di_resolution/` reference (SC-001; measured 92.7%).
- [x] T018 [US1] JSON schema test for `--report json` against `contracts/upgrade-actions.md` and pending kinds in `contracts/pending-items.md`.
- [x] T019 [US1] Idempotence: second `up` on migrated fixture → no writes, pending re-reported; resolved project → action skipped.

### Implementation

- [x] T020 [US1] `ModuleBuilder.preview_diffs()` with project-relative paths; `FileWriter` keeps path-only dry-run (H5).
- [x] T021 [US1] Implement DI `applies()` — `dependency-injector` dep, or any `src/` module importing `dependency_injector` / the root `Container` (H1).
- [x] T022 [US1] Implement DI `up()` — pyproject, libcst codemod, injectable/Injected transforms, wiring/usecases, container deletion (FR-005).
- [x] T023 [US1] SHA-256 match against the shipped 0.5.0 restapi `app.py` / `test_app.py` renders; pending `composition_root_modified` otherwise (clarification). *(Initially a regex heuristic; fixed in T044.)*
- [x] T024 [US1] Wire `commands/update_project.py`: order actions → lock → sync (H2); flags `--report`, `--skip-upgrades`, `--allow-dirty`; stderr/stdout split (M2); exit code 1 on uv failure (M3).
- [x] T025 [US1] DI action writes `scaffold_version`; runner only aligns an existing key (H4, R3).
- [x] T026 [US1] T016–T019 pass.

**Checkpoint**: US1 deliverable on fixture.

---

## Phase 5: User Story 3 — Skill and docs (P2)

### Tests first

- [x] T027 [US3] Test `install-skill migrate-di` copies files and respects `--force` (FR-012).
- [x] T028 [US3] Test recipe/guide alignment for all pending kinds (FR-013, SC-003).

### Implementation

- [x] T029 [US3] Package `skills/migrate-di/` with SKILL, recipes, errors, checklist (verification steps from retired FR-006).
- [x] T030 [US3] Implement `commands/install_skill.py` and register on CLI (L1).
- [x] T031 [US3] Add `docs/migration/dependency-injector-to-wireup.md` and README section (FR-014).
- [x] T032 [US3] T027–T028 pass.

---

## Phase 6: Polish

- [x] T033 [P] Quickstart manual run per `quickstart.md` scenarios 1–5 (git-tracked copy of the fixture, real `uv`).
- [x] T034 Full gate: `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy --strict src`, `uv run pytest`.
- [x] T035 `git grep migrate-di` — only skill name / historical notes; no CLI command references in specs or src.

---

## Phase 7: Review remediation (2026-11-20)

Findings from the post-implementation review; each fix has a regression test.

- [x] T036 Wheel build: drop duplicate `force-include` of `skills/` (wheel failed to build).
- [x] T037 Migrate `container.py` too (glob only matched `*_container.py`).
- [x] T038 `@wireup.injectable` via libcst: import placed after docstring and `__future__`; `as_type` from gateway base or use-case parameter; `lifetime="transient"` for `Factory`.
- [x] T039 `Provide`/`Depends(Provide[...])` → `Injected[<annotation>]` via libcst; remove `@inject`, `Provide`, `Container` and unused `Depends`; unannotated or after-default params → `injection_unresolved`.
- [x] T040 Realistic fixture (`gm`/`guc`/`gda`/`gep restapi` + hand wiring + `providers.Resource`), golden output and manual-resolution overlay.
- [x] T041 SC-001 metric against golden + resolution reference (was tautological).
- [x] T042 Use-case factories built from `__init__` signatures; non-provider arguments → `provider_arguments`.
- [x] T043 Containers with pending providers are kept so re-runs report them (H1); comments no longer produce findings.
- [x] T044 Composition root SHA-256 match (restapi `app.py` and `test_app.py`).
- [x] T045 `[tool.pytest.ini_options]` written as a real table; `mypy` dev dependency; `WIREUP`/`MYPY` constants reused.
- [x] T046 `--report json`: Rich and `uv` output to stderr; plain, relative, unwrapped diffs.
- [x] T047 Format only written files; runner no longer imports `commands`; single `scaffold_version` writer.
- [x] T048 Non-git tree / missing git require `--allow-dirty`; action failures exit 1.
- [x] T049 `install-skill`: name validated against packaged skills (path traversal), per-target skip, `AGENTS.md` lists real paths.
- [x] T050 028: 10 links to `specs/029-upgrade-framework/README.md` → `spec.md`; future `migrate-di` command wording → `scaffold up`.
- [x] T051 Kinds catalogue `PENDING_KINDS`/`AUTOMATED_KINDS`; guide anchors, recipes and contract aligned by test (FR-013, SC-003).
- [x] T052 Lazy libcst import verified by test (L2).
- [x] T053 E2E `tests/e2e/test_legacy_upgrade.py`: `up` + resolution → ruff, mypy --strict, pytest, `vs` green.

---

## Phase 8: User Story 4 — Pre-scaffold projects (P3)

**Goal**: Services written before the scaffolder (same layout, no `[tool.scaffold-ca-python]`, `use_cases/` and `gateway/` naming) can adopt the tooling and migrate with `scaffold up` + skill.

**Independent Test**: Copies of `code_review_smcp` / `code_review_aiagent` (outside the repo): adoption message, then dry-run classifies their use cases and gateways.

### Tests first

- [x] T054 [P] [US4] `tests/core/test_project_detector.py`: pyproject without section (root and `src/<pkg>/` cwd) raises `MissingScaffoldSectionError` naming the file and suggesting `name` from the `src/` package; root-layout CA fallback unchanged.
- [x] T055 [P] [US4] `tests/commands/test_update_project_upgrades.py`: `scaffold up` in such a tree exits 1, prints the section snippet, no traceback, nothing written.
- [x] T056 [P] [US4] `tests/factory/upgrades/test_dependency_injector_migration.py`: fixture variant renamed to `domain/use_cases/` and `gateway/` migrates with a factory, `as_type` inferred and only the `resource_provider` pending.

### Implementation

- [x] T057 [US4] `core/project_detector.py`: `MissingScaffoldSectionError` with adoption snippet (FR-016); `commands/_shared.require_project_root` always shows it.
- [x] T058 [US4] Naming variants for use cases and gateways in the DI action and `core/wiring_utils.find_missing_adapters` (FR-017).
- [x] T059 [US4] Skill: `references/pre-scaffold.md`; `SKILL.md` routing; `provider_arguments` recipe with the typed-settings conversion (FR-018).
- [x] T060 [US4] Documentation: migration guide section «Projects created before the scaffolder», README, quickstart Scenario 6, contracts/plan/research notes for the new behavior (FR-019).
- [x] T061 [US4] Full gate + legacy e2e + dry-run on the two pre-scaffold copies; record before/after automated/pending counts. *(MCP server: 10 automated / 16 pending; A2A agent: 4 / 21, its use case now recognized under `use_cases/` and reported as `provider_arguments` because it receives a `Resource` typed `Any`.)*

---

## Dependencies

```text
T001–T003 → T008–T015 → T016–T026 (US1) → T027–T032 (US3) → T033–T035
T004–T007 can parallel T009–T015 after T001
T054–T056 → T057–T059 → T060 → T061 (Phase 8 after Phase 7)
```

---

## Coverage map (plan findings → tasks)

| Finding | Coverage |
|---------|----------|
| H1 content-based | T021, research R1, FR-004 |
| H2 order | T024, research R2 |
| H3 registry order | T009, T012 |
| H4 scaffold_version | T010, T025, research R3 |
| H5 diffs | T020 |
| H6/H7 028 docs | T004–T007 |
| H8 | Done on main (1.0.1) |
| M1 persist limit | plan.md, quickstart.md |
| M2/M3 I/O & exits | T024, contracts |
| M4 dirty tree | T010, T024 |
| M5 ABC pattern | T011 |
| M6 links count | T006 |
| L1 install-skill | T030 |
| L2 libcst lazy | T022, T052 |
| L3 fixture | T003, T040 |