# Implementation Plan: SOLID refactor and comment cleanup of the scaffolder

**Branch**: `feature/022-solid-code-cleanup` | **Date**: 2026-10-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/022-solid-code-cleanup/spec.md`

## Summary

Internal refactor of `src/scaffold_ca_python/` with no change to the CLI's observable behavior, apart from the allowed changes C-1, C-2 and C-3. It has five parts.

1. **Shared command utilities.** A common layer for the commands (`commands/_shared.py`) centralizes:
   - errors with a resolution hint;
   - project-root lookup;
   - duplicate guards;
   - the dry-run tree;
   - the `--dry-run` option.
2. **Single context loader.** `load_project_context` moves to `core/project_detector.py` and fixes the `gep` inconsistency.
3. **Type knowledge lives in the factories.** Entry-point, driven-adapter and pipeline factories declare what is specific to their type through base classes with `ClassVar`s. The registries move into their `factory/` packages, so a new type does not touch `commands/`.
4. **Complexity ≤ 10.** `_add_tool_impl`, `_generate_entry_point_impl`, `FileWriter._commit`, `StructureValidator.validate` and `DeleteModuleFactory.build` are split.
5. **Comments, guardrails and output fixes.** Comments and docstrings are cleaned up (Google style, no Spec Kit IDs). Ruff `B`, `SIM` and `C90` are enabled. The `gpipe` hint (FR-016) and the `[project.scripts]` output (FR-021) are fixed.

## Technical Context

**Language/Version**: Python 3.13.

**Primary Dependencies**: Typer (with `Annotated`), Rich, Jinja2, Pydantic v2, PyYAML. No dependencies are added.

**Storage**: local files (the generated project and its `pyproject.toml`).

**Testing**: pytest, pytest-cov (≥80% gate), pytest-benchmark and `typer.testing.CliRunner`. Baseline measured on 2026-10-22: **739 passed, 1 skipped, 96.50% coverage**.

**Target Platform**: cross-platform CLI (macOS, Linux, Windows) distributed through PyPI.

**Project Type**: CLI (single project, `src/` layout).

**Performance Goals**: no regression in `tests/commands/test_performance.py`.

**Constraints**:
- Output is byte-for-byte identical in generated files, messages and exit codes. The exceptions are:
  - FR-010 (project context);
  - FR-016 (`gpipe` message);
  - FR-021 (`[project.scripts]` shown literally).
- Existing Jinja templates are not modified. Only two new ones are added (FR-004, research R-13).
- `mypy --strict` must pass.

**Scale/Scope**: about 4.4k LOC in 40 modules and 50 test files.

Violations measured today with `ruff --select B,SIM,C90` and `max-complexity=10`:
- **`src/`, 10 in total:**
  - 6 × C901: `_add_tool_impl` 26, `_generate_entry_point_impl` 24, `_generate_driven_adapter_impl` 13, `StructureValidator.validate` 13, `FileWriter._commit` 12, `DeleteModuleFactory.build` 12.
  - 2 × B904, 1 × B905 and 1 × SIM108.
- **`tests/`:** 2 × B017. No C90 violations.
- **B008:** does not appear, because Typer uses `Annotated`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Constitution version: **2.1.0**.

| Principle | Assessment | Status |
|---|---|---|
| I. Clean Architecture in generated projects | Templates and generated output don't change. `vs` keeps its logic; only the complexity of `validate` is reduced. | ✅ |
| II. Template-driven generation | `generate_project` and `generate_pipeline` switch to `TemplateRenderer.render()` with packaged templates instead of `render_string(_tmpl())`. Two files of `ca` that don't come from a template today now do, with the same output (FR-004, R-13): the root package `__init__.py` (an f-string) and the empty `src/tests/__init__.py`. They use the new templates `project/package_init.py.jinja2` and `project/empty.jinja2`. Factories still pass template contexts as `dict`, which is pre-existing debt (see Complexity Tracking). No new code introduces `dict` contexts: the `render_into` helper was dropped. | ✅ / ⚠️ pre-existing debt (Governance v2.1.0) |
| III. Command parity and `--dry-run` | Commands, aliases and flags don't change, and the parity and checksum tests are kept. | ✅ |
| IV. Python idioms | Compliance improves: consistent `X \| None` typing, extended ruff rules and strict mypy with no new `type: ignore`. | ✅ |
| V. Test-first (NON-NEGOTIABLE) | Every story starts with red tests, among them the context regression (FR-020), extensibility with a fake factory, the new `gpipe` message, the `[project.scripts]` output (FR-021), `set_project_script` and the new templates. The pure refactor is covered by the existing suite, green before and after each step. | ✅ |
| VI. Developer Experience | FR-016 fixes an invalid hint (`--force`) and FR-021 makes `[project.scripts]` visible in the output. 38 of the 56 error messages in `commands/` have no `Hint:`. FR-003 keeps them unchanged; this is pre-existing debt. | ⚠️ pre-existing debt (Governance v2.1.0) |
| VII. Branches | `feature/022-solid-code-cleanup`, with the `feature/` prefix the repo uses. | ✅ |

**Result**: the gate passes. Two pre-existing violations are kept under the "Pre-existing violations" governance clause (v2.1.0):
- VI: missing resolution hints;
- II: template contexts passed as `dict`.

The feature does not introduce or worsen either one. The follow-up spec directories are created in T063 before merge.

**Post-design re-check (Phase 1)**: ✅. The design in [data-model.md](data-model.md) and [contracts/](contracts/):
- only adds base classes, `ClassVar`s and internal utilities;
- doesn't change existing templates or flags;
- changes the output only through C-1, C-2 and C-3.

The adapted tests only change imports or where a factory is registered (see research R-08).

## Project Structure

### Documentation (this feature)

```text
specs/022-solid-code-cleanup/
├── plan.md              # This file
├── research.md          # Phase 0: design decisions
├── data-model.md        # Phase 1: internal entities (options, descriptors, context)
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── cli-behavior.md        # Observable behavior contract (+ allowed changes C-1..C-3)
│   └── factory-extension.md   # Contract for adding new types
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/scaffold_ca_python/
├── cli.py                          # no functional changes
├── commands/
│   ├── _shared.py                  # NEW: fail(), require_project_root(), validate_name_or_exit(),
│   │                               #      ensure_absent(), print_dry_run_tree(),
│   │                               #      print_pending_dependencies(), dry_run_option(), build_and_persist()
│   ├── _entry_point_rules.py       # NEW: check_flags(), check_conflicts() (research R-02/R-03)
│   ├── generate_entry_point.py     # orchestration only: options → validation → factory → presentation
│   ├── add_mcp_tool.py             # NEW: --add-tool flow extracted from generate_entry_point
│   ├── generate_driven_adapter.py  # no if/elif per type
│   ├── generate_pipeline.py        # uses ModuleBuilder + PIPELINE_PROVIDERS, injectable renderer/writer
│   ├── generate_project.py         # file table + injectable ModuleBuilder
│   ├── generate_model.py / generate_use_case.py / generate_helper.py / delete_module.py
│   │                               # no single-entry _REGISTRY; use _shared
│   ├── update_project.py           # _run_uv() removes the duplicated try/except
│   └── validate_structure.py
├── core/
│   ├── project_detector.py         # + load_project_context() (single definition)
│   ├── module_locator.py           # NEW: find_module_targets() (shared by dm and its factory)
│   ├── openapi_routes.py           # NEW: parse_routes() (formerly _parse_swagger in gep)
│   ├── module_builder.py           # + set_project_script(); no magic keys in persist()
│   ├── file_writer.py              # _commit split; zip(strict=True)
│   ├── structure_validator.py      # validate split into _classify/_parse/_violations_in
│   └── mcp_tool_spec.py, pyproject_writer.py, template_renderer.py, name_utils.py  # docstring cleanup
├── factory/
│   ├── __init__.py                 # ModuleFactory (Protocol, unchanged)
│   ├── entry_points/
│   │   ├── __init__.py             # ENTRY_POINT_FACTORIES (registry)
│   │   ├── base.py                 # NEW: EntryPointFactory, EntryPointConflict, EntryPointFlag
│   │   └── ep_restapi.py, ep_mcp.py, ep_agent.py, ep_generic.py  # declare ClassVars
│   ├── driven_adapters/
│   │   ├── __init__.py             # DRIVEN_ADAPTER_FACTORIES
│   │   ├── base.py                 # NEW: DrivenAdapterFactory
│   │   └── da_*.py
│   ├── pipelines/                  # NEW
│   │   ├── __init__.py             # PIPELINE_PROVIDERS
│   │   └── pipeline_factory.py     # PipelineFactory (github, azure as descriptor instances)
│   └── simple/                     # no structural changes; cleanup
├── models/
│   ├── context.py                  # docstring cleanup
│   └── options.py                  # NEW: EntryPointOptions (frozen dataclass)
└── templates/project/
    ├── package_init.py.jinja2      # NEW (R-13)
    └── empty.jinja2                # NEW (R-13)

tests/                              # same layout; new tests:
├── commands/test_shared.py
├── commands/test_behavior_contract.py   # US1 safety net + C-3
├── core/test_project_context.py    # FR-010/FR-020 regression
├── core/test_module_locator.py
├── core/test_openapi_routes.py
├── models/test_options.py
├── test_source_hygiene.py          # FR-015
└── factory/test_extensibility.py   # extended: fake factory with a full descriptor
```

**Structure Decision**: The single project with `src/` layout stays.
- **Registries:** type registries move from `commands/` to the `__init__.py` of each `factory/` package, so adding a type does not modify `commands/` (SC-005).
- **Shared logic:** command-shared logic lives in `commands/_shared.py` and not in `core/`, because it depends on Rich and Typer (it is presentation). `core/` stays independent of the CLI.
- **Template helpers:** the local `tpl()` helpers in the entry-point factories stay as they are. A shared `render_into()` helper was considered and dropped, because it would be new code that accepts `dict` contexts (Constitution II, Governance v2.1.0: new code must comply).

## Suggested implementation order

Each step leaves the suite green and can be its own commit:

1. **Guardrails first:** enable `B`, `SIM` and `C90` in `pyproject.toml`, with a temporary C901 `per-file-ignores` only for the affected modules. It is removed at the end. Fix B904, B905, SIM108 and B017.
2. **Shared utilities:** create and test `commands/_shared.py`.
3. **Story 1 (P1), safety net:** behavior-contract tests, green against the current code.
4. **Story 2 (P1):** `EntryPointFactory` and `DrivenAdapterFactory`, registries in `factory/`, `set_project_script()` and `PipelineFactory`.
5. **Story 3 (P2), TDD:** single `load_project_context` and its regression test.
6. **Story 4 (P2):**
   - split gep (`EntryPointOptions`, `add_mcp_tool.py`, `openapi_routes.py`), `FileWriter`, `StructureValidator`, and `delete_module` (with `module_locator`);
   - `generate_project` switches to the file table, the new templates and an injectable builder.
7. **Stories 5 and 6 (P3):**
   - comment and docstring cleanup and dead code;
   - the `gpipe` message (C-2) and the `[project.scripts]` output (C-3);
   - remove the temporary `per-file-ignores`.
8. **Final verification:** full suite, checksum, parity, generated-tree comparison ([quickstart.md](quickstart.md)), and the follow-up spec directories 023/024.

## Complexity Tracking

Pre-existing violations kept under the Constitution v2.1.0 "Pre-existing violations" governance clause:

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **VI**: 38 of 56 error messages in `commands/` have no `Hint:`. Examples: the `gep` flag validation, `Unknown type` and `--name is required…`. They are kept unchanged. | FR-003 requires the output to stay unchanged during the refactor. Adding hints would mix a UX change into the refactor. | Adding them here would invalidate the US1 safety net (T008–T010) and multiply the allowed changes. It will be resolved in follow-up feature **023-error-hints**. |
| **II**: factories pass `dict` contexts to templates. The dicts come from the already validated `ModuleContext.model_dump()`, plus `bool` flags. | Keep the output identical and the refactor scope bounded. | Typing every context with Pydantic touches all 11 factories and their templates. It will be resolved in follow-up feature **024-typed-template-contexts**. No new code in this feature adds `dict` contexts. |
