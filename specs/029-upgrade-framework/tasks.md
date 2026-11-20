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
- [x] T003 [P] Generate static fixture `tests/fixtures/legacy_050_project/` via `uvx scaffold-ca-python==0.5.0` once; commit tree + README for regeneration (L3).

---

## Phase 2: Spec 028 alignment (H6, H7, M6) — docs only

- [x] T004 Update FR-020 in `specs/028-wireup-di/spec.md`: exempt `up` with `ca` and `vs`; link to `specs/029-upgrade-framework/`; note «Superseded in part by spec 029»; replace `migrate-di` wording with `scaffold up` / `install-skill migrate-di`.
- [x] T005 Update `specs/028-wireup-di/contracts/generated-files.md` § Legacy Projects: remove `up` from refused commands; same exemption note; point migration to 029.
- [x] T006 [P] Rewrite all 22 `docs/spec-029-migrate-di` references under `specs/028-wireup-di/` to `specs/029-upgrade-framework/` (verify with `git grep -c spec-029 specs/028-wireup-di` → 0 for old path).
- [x] T007 Delete obsolete `specs/028-wireup-di/contracts/migrate-di.md`; replace cross-links with `specs/029-upgrade-framework/contracts/`.
- [x] T008 Change `_LEGACY_MIGRATION_HINT` in `src/scaffold_ca_python/commands/_shared.py` to instruct `scaffold up` (implementation with US1).

---

## Phase 3: Foundational — upgrade framework (US2)

**Goal**: Registry, ABC, runner skeleton; no DI codemod yet.

### Tests first

- [x] T009 [P] Add `tests/factory/upgrades/test_registry_order.py`: `UPGRADE_ACTIONS` module name dates are non-decreasing (H3).
- [x] T010 [P] Add `tests/factory/upgrades/test_runner_guards.py`: clean-tree rule (M4), newer `scaffold_version` skips actions (H4), dry-run writes nothing.

### Implementation

- [x] T011 [P] Create `factory/upgrades/base.py` — `UpgradeAction` ABC with ClassVar `name`, `description`, `applies`, `up` (no version fields) (M5).
- [x] T012 Create `factory/upgrades/__init__.py` — `UPGRADE_ACTIONS` list and typed registry export.
- [x] T013 Create `factory/upgrades/runner.py` — `UpgradeRunner.run()`: iterate actions, `persist_and_format` after each (M1), aggregate `UpgradeReport`.
- [x] T014 Add stub action `upgrade_2026_11_20_dependency_injector_to_wireup.py` returning empty result until US1 fills it.
- [x] T015 T009–T010 green.

**Checkpoint**: Runner callable from tests with stub action.

---

## Phase 4: User Story 1 — DI migration (P1) MVP

**Goal**: Full DI action + `up` integration + diffs + JSON report.

### Tests first

- [x] T016 [US1] Integration test: `scaffold up --dry-run` on `legacy_050_project` → no git dirty; stdout/stderr contract smoke.
- [x] T017 [US1] Golden test: apply `up` on fixture → ≥70% line delta vs manual wireup reference (SC-001).
- [x] T018 [US1] JSON schema test for `--report json` against `contracts/upgrade-actions.md` and pending kinds in `contracts/pending-items.md`.
- [x] T019 [US1] Idempotence: second `up` on migrated fixture → no applied items.

### Implementation

- [x] T020 [US1] Extend `core/file_writer.py` / `module_builder.py` for unified diffs in dry-run (H5).
- [x] T021 [US1] Implement DI `applies()` — `dependency-injector` dep or container modules present (H1).
- [x] T022 [US1] Implement DI `up()` — pyproject, libcst codemod, injectable/Injected transforms, wiring/usecases, container deletion (FR-005).
- [x] T023 [US1] Fingerprint table for 0.5.0 composition roots; pending `composition_root_modified` (clarification).
- [x] T024 [US1] Wire `commands/update_project.py`: order actions → lock → sync (H2); flags `--report`, `--skip-upgrades`, `--allow-dirty`; stderr/stdout split (M2); exit code 1 on uv failure (M3).
- [x] T025 [US1] Runner updates `scaffold_version` after applied items (H4).
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

- [ ] T033 [P] Quickstart manual run per `quickstart.md` scenarios 1–4.
- [x] T034 Full gate: `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy --strict src`, `uv run pytest`.
- [ ] T035 `git grep migrate-di` — only skill name / historical notes; no CLI command references in specs or src.

---

## Dependencies

```text
T001–T003 → T008–T015 → T016–T026 (US1) → T027–T032 (US3) → T033–T035
T004–T007 can parallel T009–T015 after T001
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
| L2 libcst lazy | T022 |
| L3 fixture | T003 |