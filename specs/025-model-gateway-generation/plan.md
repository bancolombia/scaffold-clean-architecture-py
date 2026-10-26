# Implementation Plan: Model Gateway Generation

**Branch**: `feature/model-gateway-generation` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/025-model-gateway-generation/spec.md`

## Summary

`scaffold gm --name <name>` stops writing a flat `domain/model/<name>.py`. It now writes a per-model package `domain/model/<name>/` containing the model, a `gateways/` sub-package with an empty abstract `<ClassName>Repository`, and mirrored test stubs. The change stays inside the existing model template group and `ModelFactory`. The command checks for three conflicts up front: the new package, a legacy flat file, and a leftover tests folder. Module lookup learns the new folder layout, and the delete-module factory reuses that lookup instead of keeping its own copy of the path list.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: Typer, Rich, Jinja2, Pydantic v2 (no new dependencies)

**Storage**: Files on disk, written atomically through the existing `FileWriter`

**Testing**: pytest + pytest-cov (80% gate) for the CLI. Generated projects use pytest with `--import-mode=importlib`, so test folders need no `__init__.py`.

**Target Platform**: macOS / Linux developer machines (CLI)

**Project Type**: CLI code generator

**Performance Goals**: `gm` stays under the existing 3 s benchmark (`tests/commands/test_performance.py`)

**Constraints**: Generated code must pass the generated project's `ruff` rules (`E, F, I, UP, ANN`), `mypy --strict`, and pytest without edits. Unused imports (F401) are therefore not allowed in templates.

**Scale/Scope**: 4 new templates, 1 changed template, 4 changed source modules, about 6 test files updated or extended, and a README section

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| I. Clean Architecture in generated projects | PASS | Gateway lives in `domain/`, imports only `abc`. `vs` already classifies every path under `domain/model/` (prefix match in `structure_validator.py`) as the domain model layer. |
| II. Template-driven generation | PASS | All 6 generated files come from `templates/model/*.jinja2`. New templates get rendering tests in `tests/templates/test_model_templates.py`. Context is the existing Pydantic `ModuleContext`. |
| III. Command parity | PASS | `gm` / `generate-model` keep names, aliases, and `--dry-run`. Output still lands in `domain/model/`. |
| IV. Python-first idioms | PASS | Type hints on all changed public functions; ruff and mypy strict apply. The gateway has no I/O, so the async default does not apply yet. |
| V. Test-first | PASS | Every task starts with a failing test (see Implementation Order). Generated project gets 2 test stubs. |
| VI. Developer experience | PASS | Conflict errors use `fail()` with a resolution hint. Help text and epilog describe the new layout. |
| VII. Branch naming | PASS | Work happens on `feature/model-gateway-generation` (step 0 below). |

No violations, so Complexity Tracking is empty.

**Post-design re-check (after Phase 1)**: All gates still PASS. Moving `DeleteModuleFactory` onto `find_module_targets` removes duplicated path logic and adds no new abstraction.

## Project Structure

### Documentation (this feature)

```text
specs/025-model-gateway-generation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── gm.md
│   └── dm.md
├── checklists/requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/scaffold_ca_python/
├── commands/
│   └── generate_model.py            # conflict checks (3 paths), help/epilog text
├── core/
│   └── module_locator.py            # add model-package candidate before legacy flat file
├── factory/simple/
│   ├── model_factory.py             # queue 6 files in the new layout
│   └── delete_module_factory.py     # reuse find_module_targets
└── templates/model/
    ├── __init__.py.jinja2           # NEW: model package docstring
    ├── model.py.jinja2              # unchanged
    ├── test_model.py.jinja2         # CHANGED: import from <pkg>.domain.model.<name>.<name>
    ├── gateways_init.py.jinja2      # NEW: gateways package docstring
    ├── gateway.py.jinja2            # NEW: empty ABC <ClassName>Repository
    └── test_gateway.py.jinja2       # NEW: asserts issubclass(..., ABC)

tests/
├── templates/test_model_templates.py      # rendering tests for new/changed templates
├── factory/simple/test_model_factory.py   # 6 queued paths
├── core/test_module_locator.py            # package layout + legacy layout
├── commands/test_generate_model.py        # new paths, gateway, dry-run, 3 conflicts, multi-word
├── commands/test_delete_module.py         # delete package layout; legacy flat still works
├── commands/test_workflow.py              # new model path
└── commands/test_performance.py           # cleanup removes package folders
```

**Structure Decision**: Single-project CLI. Every change fits into the existing modules listed above. No new packages are created in the CLI.

## Implementation Order

0. **Create the branch**: `git checkout main && git pull && git checkout -b feature/model-gateway-generation`. Commit the spec artifacts on this branch.
1. **Templates (test-first)**: add rendering tests, then the 4 new templates and the `test_model.py.jinja2` import change.
2. **ModelFactory (test-first)**: update `test_model_factory.py` to expect the 6 paths, then change the factory.
3. **Conflict checks (test-first)**: add the 3 conflict tests to `test_generate_model.py`, then call `ensure_absent` for the package dir, the legacy flat file, and the tests dir in `generate_model.py`.
4. **Lookup and delete (test-first)**: extend `test_module_locator.py` and `test_delete_module.py`, then add the package candidate to `find_module_targets` and make `DeleteModuleFactory` iterate its result.
5. **Update remaining tests**: fix the old flat paths in `test_workflow.py` and `test_performance.py`.
6. **Docs**: `gm` help/epilog and the README `scaffold gm` section show the new tree.
7. **Validate**: run the [quickstart](quickstart.md) end-to-end, then `uv run ruff check`, `uv run ruff format --check`, `uv run mypy`, and `uv run pytest`.

## Complexity Tracking

No constitution violations to justify.
