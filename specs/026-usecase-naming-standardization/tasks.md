---

description: "Task list for Use Case Naming Standardization"
---

# Tasks: Use Case Naming Standardization

**Input**: Design documents from `/specs/026-usecase-naming-standardization/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/guc.md, contracts/dm.md, quickstart.md

**Tests**: Included. Constitution Principle V (test-first) and spec SC-007 require them. Every test task MUST be written and seen failing before its implementation task.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story from spec.md (US1 to US4)

## Path Conventions

Single-project CLI: source in `src/scaffold_ca_python/`, CLI tests in `tests/`. Generated projects put tests in `src/tests/`.

---

## Phase 1: Setup

**Purpose**: Confirm a clean baseline on the feature branch.

- [x] T001 Confirm the current branch is `feature/usecase-naming-standardization` and run `uv run pytest` from the repo root to record the baseline (all green). Do NOT commit without asking the user.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The suffix-stripping helper used by both generation (US1 to US3) and deletion (US4).

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Add parametrized tests for `strip_usecase_suffix` in `tests/core/test_name_utils.py` covering the research R2 table: `book`→`book`, `book_usecase`→`book`, `book_use_case`→`book`, `paper_usecase_usecase`→`paper`, `paper_use_case_usecase`→`paper`, `usecase_registry`→`usecase_registry`, `bookusecase`→`bookusecase`, `usecase`→`""`, `use_case`→`""`, `usecase_usecase`→`""`. Confirm they fail.
- [x] T003 Implement `strip_usecase_suffix(name: str) -> str` in `src/scaffold_ca_python/core/name_utils.py`: prefix `_`, remove the regex `(?:_(?:usecase|use_case))+$`, drop the leading `_`. Add a one-line docstring and full type hints. T002 must pass.

**Checkpoint**: Helper ready. User story phases can begin.

---

## Phase 3: User Story 1 - Generated use case modules always carry the `_usecase` suffix (Priority: P1) MVP

**Goal**: `scaffold guc --name <base>` creates `domain/usecase/<base>_usecase.py` with `class <Base>UseCase` and `src/tests/domain/usecase/test_<base>_usecase.py`.

**Independent Test**: In a fresh project, `scaffold guc --name create_order` creates `create_order_usecase.py` (class `CreateOrderUseCase`) and `test_create_order_usecase.py`, and the generated project's tests pass.

### Tests for User Story 1 (write first, confirm they fail)

- [x] T004 [P] [US1] In `tests/templates/test_use_case_templates.py`, change `test_test_use_case_imports_class` (or add a test) to assert the rendered test template contains `from my_app.domain.usecase.create_order_usecase import CreateOrderUseCase`. Also add a test asserting `ast.parse(out)` succeeds for both rendered templates (`use_case.py.jinja2` and `test_use_case.py.jinja2`).
- [x] T005 [P] [US1] In `tests/factory/simple/test_use_case_factory.py`, change `expected_files` in `test_use_case_files_queued_in_dry_run` to `src_dir / "create_order_usecase.py"` and `test_dir / "test_create_order_usecase.py"`, and update the comment.
- [x] T006 [P] [US1] In `tests/commands/test_generate_use_case.py`, update every success-path, alias, and dry-run path to `<base>_usecase.py` / `test_<base>_usecase.py` (`create_order`, `place_order`, `cancel_order`). Add assertions that `place_order_usecase.py` contains `class PlaceOrderUseCase:` and that the success output contains `PlaceOrderUseCase`. Keep the existing error tests (`2Bad`, PascalCase, kebab-case, no project root, no arguments) unchanged: they cover FR-012.

### Implementation for User Story 1

- [x] T007 [P] [US1] In `src/scaffold_ca_python/templates/use_case/test_use_case.py.jinja2`, change the import to `from {{ project.python_package }}.domain.usecase.{{ module_name }}_usecase import {{ class_name }}UseCase`. Leave `use_case.py.jinja2` unchanged. T004 must pass.
- [x] T008 [P] [US1] In `src/scaffold_ca_python/factory/simple/use_case_factory.py`, write `src_dir / f"{snake_name}_usecase.py"` and `test_dir / f"test_{snake_name}_usecase.py"`, and update the `build` docstring paths. T005 must pass.
- [x] T009 [US1] In `src/scaffold_ca_python/commands/generate_use_case.py`, compute `base = strip_usecase_suffix(to_snake_case(name))` after `validate_name_or_exit`. Build `ModuleContext(name=base, ...)`, and set `src_path` for `ensure_absent` to `.../domain/usecase/f"{base}_usecase.py"`. The success message keeps `{module_ctx.class_name}UseCase`. T006 must pass (depends on T003, T007, T008).

**Checkpoint**: US1 works on its own. `guc --name create_order` yields `create_order_usecase.py` / `CreateOrderUseCase`.

---

## Phase 4: User Story 2 - The suffix is never duplicated (Priority: P1)

**Goal**: `<base>`, `<base>_usecase`, `<base>_use_case`, and repeated suffixes all produce identical output. A name made only of the suffix fails.

**Independent Test**: `guc --name book_usecase` and `guc --name book_use_case` each produce `book_usecase.py` with `class BookUseCase`, the same as `guc --name book`. `guc --name usecase` exits 1 and writes nothing.

### Tests for User Story 2 (write first, confirm they fail)

- [ ] T010 [US2] Add tests to `tests/commands/test_generate_use_case.py`:
  - one test `test_all_spellings_produce_identical_output`: for each of `book`, `book_usecase`, `book_use_case`, `book_usecase_usecase`, `book_use_case_usecase` in turn, run `guc`, read `book_usecase.py` and `test_book_usecase.py`, assert `class BookUseCase:` is present and `BookUsecaseUseCase` is absent, then delete both files. After the loop, assert every collected pair of contents is identical (FR-006, SC-002).
  - `create_order_usecase` produces `create_order_usecase.py` / `CreateOrderUseCase`.
  - `usecase_registry` produces `usecase_registry_usecase.py` / `UsecaseRegistryUseCase`.
  - parametrize over `usecase`, `use_case`, `usecase_usecase`: exit code 1, output contains `is only the 'usecase' suffix` and `create_order`, and `domain/usecase/` has no new files (FR-008).

### Implementation for User Story 2

- [ ] T011 [US2] In `src/scaffold_ca_python/commands/generate_use_case.py`, right after computing `base` and before `require_project_root()`, call `fail(f"Use case name '{name}' is only the 'usecase' suffix.", hint="Use a descriptive name such as 'create_order'.")` when `base` is empty. Import `fail` from `scaffold_ca_python.commands._shared`. T010 must pass.

**Checkpoint**: US1 and US2 both pass. No input produces a doubled suffix.

---

## Phase 5: User Story 3 - Preview and conflict detection use the normalized name (Priority: P2)

**Goal**: `--dry-run` lists the normalized paths. An existing `<base>_usecase.py` blocks every spelling. Legacy `<base>.py` is ignored.

**Independent Test**: `guc --name book_usecase --dry-run` lists `book_usecase.py` and `test_book_usecase.py` and writes nothing. After `guc --name book`, `guc --name book_use_case` exits 1.

### Tests for User Story 3 (write first, confirm they fail)

- [ ] T012 [US3] Add tests to `tests/commands/test_generate_use_case.py`:
  - `guc --name create_order_usecase --dry-run` exits 0, the output contains the tree title `create_order_usecase (dry run)`, `create_order_usecase.py`, and `test_create_order_usecase.py`, and not `create_order_usecase_usecase`, and nothing is written.
  - the dry-run path list equals the set of files a real run then creates (FR-010, SC-005).
  - after `guc --name create_order`, each of `create_order`, `create_order_usecase`, `create_order_use_case` exits 1 with `already exists` in the output, and the existing file content is unchanged (FR-009, SC-006).
  - with only `src/tests/domain/usecase/test_create_order_usecase.py` present (written by the test), `guc --name create_order` exits 1 with `already exists` in the output and creates no source file (FR-009b).
  - with a pre-existing `src/my_app/domain/usecase/create_order.py` (written by the test), `guc --name create_order` exits 0, creates `create_order_usecase.py`, leaves `create_order.py` byte-identical, and prints no warning about it (FR-009a).

### Implementation for User Story 3

- [ ] T013 [US3] In `src/scaffold_ca_python/commands/generate_use_case.py`, change the dry-run call to `print_dry_run_tree(f"{base}_usecase", created, project_root)`. Confirm the conflict check from T009 already uses `<base>_usecase.py`. Add a second `ensure_absent` call for `resolve_tests_root(project_root) / "domain" / "usecase" / f"test_{base}_usecase.py"` with the same hint (import `resolve_tests_root` from `scaffold_ca_python.core.project_detector`). T012 must pass.

**Checkpoint**: US1 to US3 pass. Preview and conflict checks agree with the generated names.

---

## Phase 6: User Story 4 - Delete a use case by base name or suffixed name (Priority: P3)

**Goal**: `dm --name <base>` and `dm --name <base>_usecase` find `<base>_usecase.py` and its test. Legacy `<name>.py` is still found. When both layouts exist, all are listed and removed.

**Independent Test**: After `guc --name book`, both `dm --name book --confirm` and `dm --name book_usecase --confirm` (in separate projects) remove `book_usecase.py` and `test_book_usecase.py`.

### Tests for User Story 4 (write first, confirm they fail)

- [ ] T014 [P] [US4] Add tests to `tests/core/test_module_locator.py` (use `_make_project`, which has no `domain/usecase` folder, so create it):
  - `<base>_usecase.py` plus `tests/domain/usecase/test_<base>_usecase.py` are found for `snake="book"` and for `snake="book_usecase"`.
  - for `snake="book_usecase"`, the result contains `book_usecase.py` exactly once (dedupe).
  - with both `book.py` and `book_usecase.py` present, `snake="book"` returns both, with `book_usecase.py` first.
  - a legacy `book.py` alone is still found for `snake="book"`.
  - `snake="usecase"` with no files returns `[]` (empty base skipped).
- [ ] T015 [P] [US4] Add tests to `tests/commands/test_delete_module.py` with a new fixture `project_root_with_use_case` that runs `ca --name my-app` and `guc --name book`:
  - `dm --name book --confirm` and `dm --name book_usecase --confirm` each remove `src/my_app/domain/usecase/book_usecase.py` and `src/tests/domain/usecase/test_book_usecase.py`.
  - `dm --name book` without `--confirm` lists both paths and removes nothing.
  - with an extra legacy `book.py` and `test_book.py` written by the test, `dm --name book` lists all 4 files, and `--confirm` removes all 4 (FR-014a).
  - after also running `gm --name book`, `dm --name book` without `--confirm` lists `domain/model/book`, its tests folder, `book_usecase.py`, and `test_book_usecase.py`, and removes nothing (US4 scenario 6).

### Implementation for User Story 4

- [ ] T016 [US4] In `src/scaffold_ca_python/core/module_locator.py`, compute `base = strip_usecase_suffix(snake)`. When `base` is non-empty, add the candidate `(domain/usecase/f"{base}_usecase.py", tests/domain/usecase/f"test_{base}_usecase.py")` before the existing `domain/usecase/f"{snake}.py"` candidate, and skip the legacy candidate when its path equals the new one. Update the module docstring. T014 and T015 must pass.
- [ ] T017 [P] [US4] In `src/scaffold_ca_python/factory/simple/delete_module_factory.py`, update the `build` docstring line to `domain/usecase/<base>_usecase.py or domain/usecase/<snake>.py (legacy)`. No logic change.

**Checkpoint**: All four user stories pass independently.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T018 [P] In `tests/commands/test_workflow.py` (`test_workflow_guc_creates_use_case`), change the asserted path to `.../domain/usecase/create_order_usecase.py`.
- [ ] T019 [P] In `tests/commands/test_performance.py` (`test_guc_performance`), change `--name PerfCase` to `--name perf` and the cleanup paths to `domain/usecase/perf_usecase.py` and `src/tests/domain/usecase/test_perf_usecase.py` (research R7).
- [ ] T020 In `src/scaffold_ca_python/commands/generate_use_case.py`, update `_GUC_EPILOG` to the example in `contracts/guc.md` (shows `create_order_usecase.py`).
- [ ] T021 [P] In `README.md` (`### scaffold guc` section), state that the command creates `domain/usecase/<name>_usecase.py` with class `<Name>UseCase`, and that `_usecase` in `--name` is optional and never duplicated.
- [ ] T022 Run every scenario in `specs/026-usecase-naming-standardization/quickstart.md` in a temp directory and confirm the expected outputs. Step 4 (generated project lint, format, type-check, and tests) is the verification for SC-004.
- [ ] T023 Run `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, and `uv run pytest` (coverage at or above 80%) from the repo root. All must pass. Ask the user before committing.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: after Setup. Blocks all stories (T003 is used by T009 and T016).
- **US1 (Phase 3)**: after Foundational.
- **US2 (Phase 4)** and **US3 (Phase 5)**: after US1, because they edit the same command file (`generate_use_case.py`) and extend the same test file.
- **US4 (Phase 6)**: after Foundational only. Independent of US1 to US3 for the locator tests. The `test_delete_module.py` fixture uses `guc`, so T015 passes only once US1 is done.
- **Polish (Phase 7)**: after all stories.

### Within Each Story

- Tests first, confirmed failing, then implementation.
- In US1, T007 and T008 come before T009.

### Parallel Opportunities

- US1: T004, T005, T006 together, then T007 and T008 together.
- US4: T014 and T015 together. T017 can run alongside T016.
- US4's locator work (T014, T016) can run in parallel with US1 to US3, since it touches different files.
- Polish: T018, T019, T021 together.

---

## Parallel Example: User Story 1

```bash
Task: "Update template import test in tests/templates/test_use_case_templates.py"
Task: "Update expected paths in tests/factory/simple/test_use_case_factory.py"
Task: "Update paths and class assertions in tests/commands/test_generate_use_case.py"

Task: "Change import in src/scaffold_ca_python/templates/use_case/test_use_case.py.jinja2"
Task: "Write <base>_usecase.py paths in src/scaffold_ca_python/factory/simple/use_case_factory.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 and Phase 2 (helper).
2. Phase 3 (US1). Validate with `guc --name create_order`.
3. Stop and review with the user.

### Incremental Delivery

1. US1: new file naming.
2. US2: no doubled suffix, suffix-only error (the reported bug).
3. US3: dry-run and conflict alignment.
4. US4: delete-module lookup.
5. Polish: remaining tests, docs, full validation.

---

## Notes

- `book`, `paper`, `create_order` are example names. The rules apply to any `--name`.
- `ModuleContext` and `use_case.py.jinja2` MUST NOT change (shared by other generators / already correct).
- Do not commit at any point without asking the user.
