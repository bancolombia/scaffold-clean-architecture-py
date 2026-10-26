# Implementation Plan: Use Case Naming Standardization

**Branch**: `feature/usecase-naming-standardization` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/026-usecase-naming-standardization/spec.md`

## Summary

`scaffold guc --name <name>` always writes `domain/usecase/<base>_usecase.py` with `class <Base>UseCase`. `<base>` is `--name` with any trailing `_usecase` / `_use_case` suffixes removed, so the suffix never appears twice. A single helper, `strip_usecase_suffix`, in `name_utils` does the normalization. The command passes the base name into the existing `ModuleContext`. The factory and the test template append `_usecase`. Module lookup gains one candidate (`<base>_usecase.py`) ahead of the legacy `<name>.py`, so delete-module finds use cases by base name, by suffixed name, and in both layouts, with no change to the delete factory.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Typer, Rich, Jinja2, Pydantic v2 (no new dependencies)

**Storage**: Files on disk via the existing `FileWriter`

**Testing**: pytest + pytest-cov (80% gate)

**Target Platform**: macOS / Linux developer machines (CLI)

**Project Type**: CLI code generator

**Performance Goals**: `guc` stays under the existing 3 s benchmark (`tests/commands/test_performance.py`)

**Constraints**: Generated code must pass the generated project's ruff, mypy strict, and pytest without edits. `ModuleContext` is shared by all generators and must not change behavior.

**Scale/Scope**: 1 changed template, 4 changed source modules, about 7 test files updated or extended, and a README section

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Clean Architecture in generated projects | PASS | Files still land in `domain/usecase/`. `vs` classifies by the `("domain", "usecase")` prefix, so file names do not matter. |
| II. Template-driven generation | PASS | Both files still come from `templates/use_case/*.jinja2`. The changed test template gets a rendering test for the new import. Context is the existing Pydantic `ModuleContext`. |
| III. Command parity | PASS | `guc` / `generate-use-case` and `dm` / `delete-module` keep names, aliases, and `--dry-run`. |
| IV. Python-first idioms | PASS | `strip_usecase_suffix` is fully typed; ruff and mypy strict apply. |
| V. Test-first | PASS | Every step below starts with a failing test. The generated project still gets its test stub. |
| VI. Developer experience | PASS | The new suffix-only error uses `fail()` with a hint. The help epilog shows the generated file name. |
| VII. Branch naming | PASS | Work happens on `feature/usecase-naming-standardization`, already created from `main`. |

No violations, so Complexity Tracking is empty.

**Post-design re-check (after Phase 1)**: All gates still PASS. The design adds one pure function and one lookup candidate, with no new abstractions.

## Project Structure

### Documentation (this feature)

```text
specs/026-usecase-naming-standardization/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── guc.md
│   └── dm.md
├── checklists/requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/scaffold_ca_python/
├── core/
│   ├── name_utils.py               # NEW fn: strip_usecase_suffix(name) -> str
│   └── module_locator.py           # add <base>_usecase.py candidate before <name>.py, dedupe
├── commands/
│   └── generate_use_case.py        # normalize name, empty-base error, src + test conflict checks, dry-run title, epilog
├── factory/simple/
│   ├── use_case_factory.py         # write <base>_usecase.py / test_<base>_usecase.py
│   └── delete_module_factory.py    # docstring only (lookup already shared)
└── templates/use_case/
    ├── use_case.py.jinja2          # unchanged
    └── test_use_case.py.jinja2     # CHANGED: import from ...usecase.{{ module_name }}_usecase

tests/
├── core/test_name_utils.py                 # strip_usecase_suffix table (research R2)
├── core/test_module_locator.py             # base name, suffixed name, both layouts, dedupe
├── templates/test_use_case_templates.py    # new import path
├── factory/simple/test_use_case_factory.py # new queued paths
├── commands/test_generate_use_case.py      # new paths, 3 spellings, repeated suffix, empty base, conflict, legacy ignored, dry-run
├── commands/test_delete_module.py          # delete by base / suffixed name, both layouts
├── commands/test_workflow.py               # new use case path
└── commands/test_performance.py            # --name perf, cleanup perf_usecase.py / test_perf_usecase.py
```

**Structure Decision**: Single-project CLI. Every change fits into existing modules. No new packages.

## Implementation Order

0. **Branch**: already on `feature/usecase-naming-standardization` (from `main`). Do not commit without asking the user.
1. **Name helper (test-first)**: add the R2 table as parametrized tests in `test_name_utils.py`, then implement `strip_usecase_suffix`.
2. **Template (test-first)**: assert the new import in `test_use_case_templates.py`, then change `test_use_case.py.jinja2`.
3. **Factory (test-first)**: expect `create_order_usecase.py` / `test_create_order_usecase.py` in `test_use_case_factory.py`, then change `use_case_factory.py`.
4. **Command (test-first)**: update and extend `test_generate_use_case.py` per [contracts/guc.md](contracts/guc.md), then normalize the name in `generate_use_case.py` (empty-base `fail()`, base-name `ModuleContext`, conflict path, dry-run title, epilog).
5. **Lookup and delete (test-first)**: extend `test_module_locator.py` and `test_delete_module.py` per [contracts/dm.md](contracts/dm.md), then add the candidate in `module_locator.py` and update the `DeleteModuleFactory` docstring.
6. **Remaining tests**: fix paths in `test_workflow.py` and the name and cleanup in `test_performance.py` (research R7).
7. **Docs**: the README `scaffold guc` section notes the `<name>_usecase.py` output and that `_usecase` in `--name` is optional.
8. **Validate**: run the [quickstart](quickstart.md), then `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, and `uv run pytest`.

## Complexity Tracking

No constitution violations to justify.
