# Research: Use Case Naming Standardization

## R1. Where the name is normalized

- **Decision**: `generate_use_case.py` strips the suffix right after name validation and builds `ModuleContext(name=<base>, ...)`. All downstream names derive from the base name: `class_name` gives `<Base>` and `module_name` gives `<base>`. The factory and the test template append `_usecase`.
- **Rationale**: `ModuleContext` is shared by every generator, so changing its computed fields would affect models, adapters, and helpers (out of scope). Passing the base name keeps the existing `{{ class_name }}UseCase` template line correct and fixes the doubled suffix with no template logic.
- **Alternatives considered**:
  - A use-case-specific context model with a `usecase_module` field. Rejected because it adds a type for one string concatenation.
  - Stripping inside the Jinja template. Rejected because the file path is built in Python, not in the template, so the logic would be split across two places.

## R2. Suffix-stripping rule

- **Decision**: Add `strip_usecase_suffix(name: str) -> str` to `core/name_utils.py`. It prefixes the name with `_`, removes `(?:_(?:usecase|use_case))+$`, and drops the leading `_`.
- **Rationale**: The leading `_` lets one regex handle both `book_usecase` and the suffix-only names `usecase` and `use_case` (which become empty), while `bookusecase` and `usecase_registry` stay untouched. The `+` removes repeated suffixes in any mix of spellings (clarification 2026-10-26).

| Input | Base |
|---|---|
| `book` | `book` |
| `book_usecase` / `book_use_case` | `book` |
| `paper_usecase_usecase` / `paper_use_case_usecase` | `paper` |
| `usecase_registry` | `usecase_registry` |
| `bookusecase` | `bookusecase` |
| `usecase` / `use_case` / `usecase_usecase` | empty |

- **Alternatives considered**: A `while name.endswith(...)` loop. It works but needs a separate case for the bare `usecase` / `use_case` names.

## R3. Empty base name

- **Decision**: If the base is empty, call `fail()` with the message `Use case name '<name>' is only the 'usecase' suffix.` and the hint `Use a descriptive name such as 'create_order'.` This happens before the project-root lookup, right after `validate_name_or_exit`.
- **Rationale**: Reuses the existing `fail()` helper (exit 1 plus hint, Principle VI). Failing before any path is computed guarantees nothing is written.

## R4. Template change

- **Decision**: Only `test_use_case.py.jinja2` changes. Its import becomes `from {{ project.python_package }}.domain.usecase.{{ module_name }}_usecase import {{ class_name }}UseCase`. `use_case.py.jinja2` is unchanged.
- **Rationale**: With the base name in context, the class line is already right. Only the module path in the import has to match the new file name.

## R5. Lookup and deletion

- **Decision**: In `find_module_targets`, add a use case candidate `domain/usecase/<base>_usecase.py` (with `test_<base>_usecase.py`). It comes before the existing `domain/usecase/<snake>.py` candidate, which stays as the legacy lookup. If both candidates resolve to the same path (input already suffixed), it is added once. If the base is empty, the new candidate is skipped.
- **Rationale**: `DeleteModuleFactory` already iterates `find_module_targets`, so delete-module and its preview pick up the change with no edit there. Keeping the legacy candidate satisfies FR-014. Checking both candidates satisfies FR-014a, where both layouts are listed and removed.

| `dm --name` | Files checked |
|---|---|
| `book` | `book_usecase.py`, then `book.py` |
| `book_usecase` | `book_usecase.py` (once) |
| `book_use_case` | `book_usecase.py`, then `book_use_case.py` |

- **Alternatives considered**: Normalizing the name in `delete_module.py` before lookup. Rejected because the legacy `<name>.py` file (and models or helpers whose name ends in `_usecase`) would no longer be found.

## R6. Conflict check

- **Decision**: `ensure_absent` checks both `src/<pkg>/domain/usecase/<base>_usecase.py` and `src/tests/domain/usecase/test_<base>_usecase.py`. Legacy `<base>.py` is not checked (clarification 2026-10-26, FR-009a).
- **Rationale**: All three spellings resolve to the same paths, so these checks cover FR-009. Checking the test file up front (FR-009b) avoids the `FileWriter` pre-flight raising an unhandled `FileExistsError` after parent folders were created. Feature 025 (research R4) found and fixed the same problem for models.

## R7. Existing tests that encode the old names

- **Decision**: Update the paths in `tests/commands/test_generate_use_case.py`, `tests/factory/simple/test_use_case_factory.py`, `tests/commands/test_workflow.py`, and `tests/commands/test_performance.py`. In `test_performance.py`, also change `--name PerfCase` to `perf`, which generates `perf_usecase.py` with `class PerfUseCase`.
- **Rationale**: `PerfCase` has been rejected by snake_case validation since feature 017, so the benchmark measures an error path today. Fixing the name makes it time real generation, and the cleanup has to delete `perf_usecase.py` and `test_perf_usecase.py`. The base name `perf` follows the new convention (the suffix comes from the generator). `perf_case` would produce `perf_case_usecase.py`, mixing "case" and "use case".
- **Alternatives considered**: `--name perf_usecase`. It produces the same files, but the benchmark should time the plain generation path. Suffix stripping is already covered by the unit and command tests.
