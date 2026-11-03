# Implementation Plan: Wireup DI Migration

**Branch**: `feature/028-wireup-di` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/028-wireup-di/spec.md`

---

## Summary

Replace `dependency-injector` with `wireup==2.13.0` in all generated projects. Generated projects gain a validated async dependency graph (discovered by package scan), typed adapter settings, and entry points that inject by type without importing from `application`. Eight commands are updated; two bugs are fixed; a new `migrate-di` command (libcst codemod + guide + agent skill) provides a complete upgrade path for existing 0.5.0 projects.

---

## Post-generation Validation Findings (ms_library)

The following issues were discovered by running `uv run ruff check .` and `uv run pytest` on a project generated with `ca` + `gm book` + `guc --name book --uses book_repository`.

| # | Origin | Finding | Root cause |
|---|--------|---------|------------|
| H1 | pytest | `test_book_raises_not_implemented` fails: `TypeError: BookUseCase.__init__() missing 'book_repository'` | `test_use_case.py.jinja2` always calls `UseCase()` without considering `gateways` |
| H2 | ruff | `I001` in `application/config/usecases/book_usecase.py`: gateway import adjacent to `import wireup`, extra blank line before the use-case import | Spacing in `use_case_factory.py.jinja2`; imports not sorted by module path |
| H3 | pytest | Coverage 29%, below `--cov-fail-under=75` | `ca` generates no tests for `config.py`, `wiring.py`, `main.py`; `guc --uses` generates no factory test |
| H4 | review | `create_container()` raises `WireupError` but the user gets no next-step hint | `generate_use_case.py` prints nothing when no adapter is found |
| H5 | review | `gda --gateway` not implemented; T021 and FR-009 marked done, but `as_type=` only appears in a docstring | CLI option, validation, and template rendering all missing |
| H6 | review | SC-1/FR-007 require `mypy --strict`; pyproject has no mypy; e2e tests removed it | `pyproject_toml.jinja2` dev group incomplete |
| H7 | review | `@pytest.mark.asyncio` unnecessary with `asyncio_mode = "auto"` | Test templates for use_case, agent, and generic |
| H8 | spec | FR-006 says `<name>.py`; implementation uses `<name>_usecase.py` | Spec inconsistency — fixed: `<name>_usecase.py` is canonical |
| H9 | request | Remove all legacy dependency-injector code; 0.5.0 projects → `migrate-di` only | Replace `warn_legacy_project` with `require_wireup_project` (exit 1) |
| H10 | request | `di = "wireup"` records a decision; `scaffold_version = "<version>"` is more general | Replace key, detect legacy by absence of `scaffold_version` |
| H11 | pytest | After `ca` + `gm` + `guc --uses` both wiring tests fail, not only the use-case one | Wireup validates the whole graph in `create_container()`; one missing adapter fails every wiring test |
| H12 | mypy | `Unused "type: ignore"` in generated `_Fake<Gw>` stubs | Gateway ABC has no abstract methods |
| H13 | ruff format | `config.py`, use-case factory and wiring stubs not formatter-clean | Missing blank line after docstring / between functions |
| H14 | review | `gda --gateway` never appended its wiring test; template had no `await`, resolved the concrete class | Stub template never rendered |

**Decisions**: (a) `ca` generates `test_wiring.py`; `guc --uses` and `gda --gateway` append to it (idempotent); (b) mypy added to dev group; (c) guard replaces warning; (d) `scaffold_version` replaces `di`; (e) `test_wiring.py` carries `MISSING_ADAPTERS` plus one module-level strict xfail (graph-wide validation), maintained by `guc`, `gda` and `dm`.

| # | Origin | Finding | Source | Task / re-test status (2026-10-30) |
|---|--------|---------|--------|----------------------------------|
| H15 | Post-gen | `test_config.py.jinja2` only imports the module — `config.py` and `Settings` defaults never exercised; `--cov-fail-under=75` breaks after `ca`+`gm` | test_config.py.jinja2 | Phase 3.3 T101 — mitigated; pytest passes at all nine milestones |
| H16 | Post-gen | `REST_CONSUMER_BASE_URL` fixture is scoped to `test_rest_consumer.py` — `test_wiring.py` fails to resolve the container (D5: required field) | test_rest_consumer.py.jinja2, da_rest_consumer.py | Phase 3.3 T102 — mitigated; wiring resolves after the adapter exists |
| H17 | Post-gen | Missing third-party/first-party import separation in the adapter; conftest spacing | rest_consumer.py.jinja2 | Mitigated in re-test 3; all nine Ruff runs exit 0; T103 complete |
| H18 | Post-gen | `**kwargs: object` passed to httpx → 16 mypy errors; pydantic plugin missing in mypy.ini → 1 call-arg error | rest_consumer.py.jinja2, mypy_ini.jinja2 | Phase 3.3 T104 — mitigated; mypy passes at all nine milestones |
| H19 | Re-test | Missing blank line before decorators in generated settings and conftest | rest_consumer_settings.py.jinja2, da_rest_consumer.py | Mitigated in re-test 2; all nine formatting runs exit 0 |
| H20 | Re-test 3 | Generated `test_main.py` uses `capsys: object` and incorrect `ignore[union-attr]`; expanded mypy reports attr-defined and unused-ignore | test_main.py.jinja2 | Mitigated; **T105 complete (re-test 4, 2026-11-03):** 3/3 E2E pass with `mypy --strict src/` |

These findings are tracked in Phase 3.1 (T075–T091), Phase 3.2 (T092–T100), and Phase 3.3 (T101–T108). Re-test 4 closes **T105** (parametrized rest-consumer E2E). Phase 3.3 tasks T101–T108 are complete; optional follow-up: extend T105 to assert quality at intermediate milestones after each scaffold command.

Re-test evidence: [scenario 1](../../docs/qa-report-escenario-01-ms_library.md#9-re-test--2026-10-30-t107), [scenario 2](../../docs/qa-report-escenario-02-ms_library.md#9-re-test--2026-10-30-t107), [scenario 3](../../docs/qa-report-escenario-03-ms_library.md#10-re-test--2026-10-30-t107), [focused regression failures](../../docs/.qa-logs/retest-2026-10-30/regresion-rest-consumer.log).

Latest re-test (round 3, requested 2026-10-30 17:18 -05:00): 36/36 manual checks pass. Focused regression: exit 1, 3 E2E failed on H20, 9 unit tests passed. [Current consolidated findings](../../docs/qa-scaffold-ms-library-hallazgos.md#re-test-3--2026-10-30-solicitado-a-las-1718--0500).

---

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**:
- `wireup==2.13.0` (generated projects, replaces `dependency-injector`)
- `libcst` (scaffolder, for the `migrate-di` codemod)
- `pydantic-settings` (unchanged, already in generated projects)
- `Jinja2`, `typer`, `rich` (unchanged, scaffolder)

**Storage**: N/A (code-generation tool; no database)

**Testing**: `pytest` + `pytest-cov` (scaffolder); `pytest-asyncio` (generated projects)

**Target Platform**: macOS / Linux; Python 3.13+ with `uv`

**Project Type**: CLI tool (scaffolder) that generates Python project skeletons

**Performance Goals**: No regression in command execution time; all existing tests continue to pass

**Constraints**: Must not break any existing `generate-*` command for new (wireup) projects; legacy projects (missing `scaffold_version` key) are refused (exit 1) with a message pointing to `scaffold migrate-di` / `scaffold migrate-di --install-skill` — no legacy templates are shipped

**Scale/Scope**: 8 commands modified, 1 new command (`migrate-di`), ~30 files in the scaffolder, ~15 template files replaced/added

---

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Clean Architecture in generated projects | ✅ | Entry points use `Injected[...]`; domain stays decorator-free; `validate-structure` enforced |
| II — Tests first; `tests/templates/` per group | ✅ | All implementation blocks follow red-green-refactor; `tests/templates/test_di_config_templates.py` is rewritten; new end-to-end and golden tests added |
| III — Command table and aliases | ✅ | `migrate-di` alias `mdi`; `guc` keeps `guc`; all existing aliases preserved |
| IV — Python-first idioms (async, ruff, mypy strict) | ✅ | D2 enforces async-first; FR-003 mandates ruff ASYNC rule + asyncio_mode=auto |
| V — Test-first development, 80% coverage gate | ✅ | Tests precede implementation in each block |
| VI — DX: dry-run, aliases, hints, help examples | ✅ | `migrate-di` has `--dry-run`; FR-021 hint; FR-005 helper-vs-gateway hint |
| VII — Branch naming | ✅ | `feature/028-wireup-di` |

---

## Project Structure

### Documentation (this feature)

```text
specs/028-wireup-di/
├── plan.md              ← this file
├── research.md          ← Phase 0
├── data-model.md        ← Phase 1
├── quickstart.md        ← Phase 1
├── contracts/
│   ├── generated-files.md    ← per-command file layout
│   └── migrate-di.md         ← migrate-di interface (flags, exit codes, report schema)
├── checklists/
│   └── requirements.md
└── tasks.md             ← /speckit-tasks (not yet created)
```

### Source Code (repository root)

```text
src/scaffold_ca_python/
├── cli.py                                       # register migrate-di + alias mdi
├── commands/
│   ├── generate_project.py                      # replace _DI_CONFIG_FILES
│   ├── generate_use_case.py                     # add --uses option
│   ├── generate_driven_adapter.py               # no new args; factory changes
│   ├── generate_helper.py                       # no new args; factory changes
│   ├── generate_entry_point.py                  # dispatch wireup vs legacy
│   ├── add_mcp_tool.py                          # wireup stub
│   ├── delete_module.py                         # also deletes usecase factory
│   └── migrate_di.py                            # NEW
├── core/
│   ├── project_detector.py                      # load_project_context reads di=
│   └── migrations/
│       └── di_wireup.py                         # NEW — libcst transforms
├── factory/
│   ├── simple/
│   │   ├── use_case_factory.py                  # generate factory file
│   │   ├── helper_factory.py                    # @injectable
│   │   └── delete_module_factory.py             # delete factory file too
│   ├── driven_adapters/
│   │   ├── da_generic.py                        # @injectable
│   │   ├── da_rest_consumer.py                  # @injectable + settings + config
│   │   └── da_secrets.py                        # @injectable + settings
│   └── entry_points/
│       ├── ep_restapi.py                        # wireup.integration.fastapi
│       ├── ep_mcp.py                            # inject_from_container
│       ├── ep_agent.py                          # async composition root, fix class name
│       └── ep_generic.py                        # async composition root, fix run import
├── models/
│   └── context.py                               # add di field to ProjectContext
├── skills/
│   └── migrate-di/                              # NEW — packaged in wheel
│       ├── SKILL.md
│       └── references/
│           ├── recipes.md
│           ├── errors.md
│           └── checklist.md
└── templates/
    ├── project/
    │   ├── pyproject_toml.jinja2                # wireup, ruff ASYNC, asyncio_mode
    │   └── application/config/
    │       ├── wiring.py.jinja2                 # NEW
    │       ├── config.py.jinja2                 # only global settings
    │       └── usecases/
    │           └── __init__.py.jinja2           # NEW
    ├── use_case/
    │   ├── use_case.py.jinja2                   # constructor from --uses
    │   └── use_case_factory.py.jinja2           # NEW — one per use case
    ├── helper/
    │   └── helper.py.jinja2                     # @injectable + docstring
    ├── driven_adapter/
    │   ├── generic/
    │   │   └── adapter.py.jinja2                # @injectable
    │   ├── rest_consumer/
    │   │   ├── rest_consumer.py.jinja2          # @injectable + settings
    │   │   └── rest_consumer_config.py.jinja2   # NEW — async client resource
    │   └── secrets/
    │       └── secrets_adapter.py.jinja2        # @injectable + settings
    └── entry_point/
        ├── restapi/
        │   ├── app.py.jinja2                    # wireup.integration.fastapi
        │   ├── rest_controller.py.jinja2        # Injected[...] example
        │   └── test_rest_controller.py.jinja2   # override.injectable example
        ├── mcp/
        │   ├── app.py.jinja2                    # inject_from_container
        │   ├── tools.py.jinja2                  # Injected[...], no @inject
        │   ├── prompts.py.jinja2                # Injected[...], no @inject
        │   └── resources.py.jinja2              # Injected[...], no @inject
        ├── agent/
        │   ├── agent_app.py.jinja2              # NEW — async with create_agent()
        │   └── entrypoint_main.py.jinja2        # fix missing run import
        └── generic/
            ├── generic_app.py.jinja2            # NEW — async with create_generic()
            └── entrypoint_main.py.jinja2        # fix missing run import

tests/
├── commands/
│   ├── test_generate_project.py                 # update DI assertions
│   ├── test_generate_use_case.py                # --uses scenarios
│   ├── test_generate_entry_point.py             # wireup end-to-end
│   └── test_migrate_di.py                       # NEW — golden + dry-run + idempotent
├── core/
│   └── test_di_wireup_transforms.py             # NEW — libcst transform unit tests
├── factory/
│   └── fixtures/
│       └── dry_run_baseline.json                # update for wireup file layout
├── templates/
│   └── test_di_config_templates.py              # rewrite for wiring.py/usecases/
└── fixtures/
    └── legacy_project_050/                      # NEW — 0.5.0 golden fixture

docs/
└── migration/
    └── dependency-injector-to-wireup.md         # NEW — complete migration guide
```

---

## Complexity Tracking

No constitution violations. All new code complies with every principle.

---

## Implementation Blocks

> These blocks map directly to the plan blocks in the implementation notes. Each block follows red-green-refactor. No `git commit` without explicit user authorization.

### Block A — ProjectContext and project detection

**Files**: `models/context.py`, `core/project_detector.py`, `templates/project/pyproject_toml.jinja2`, `commands/_shared.py`

**Changes**:
1. Add `scaffold_version: str | None = None` to `ProjectContext` and `is_legacy` property (`scaffold_version is None`). Legacy projects that lack the key are detected by absence, not version comparison.
2. `load_project_context` reads the `scaffold_version` key from `[tool.scaffold-ca-python]`.
3. `pyproject_toml.jinja2` emits `scaffold_version = "{{ scaffold_version }}"`.
4. Add `require_wireup_project(ctx: ProjectContext)` guard in `_shared.py` for all project-modifying `generate-*` commands; exits 1 with message pointing to `scaffold migrate-di` and `scaffold migrate-di --install-skill` when `ctx.is_legacy`.

**Tests first**:
- `test_project_context_scaffold_version`: `scaffold_version` is `None` for a project without the key (`is_legacy=True`); non-None for a project that has it.
- `test_require_wireup_project`: a legacy project causes `require_wireup_project` to exit 1 with a message naming both `migrate-di` and `--install-skill`.

---

### Block B — `generate-project` (wireup templates)

**Files**: `commands/generate_project.py`, plus new/moved templates

**Changes**:
1. Replace `_DI_CONFIG_FILES` tuple: generate `__init__.py`, `config.py`, `wiring.py`, and `usecases/__init__.py` instead of the four container files.
2. Remove the four `*_container.py.jinja2` and `container.py.jinja2` (legacy templates no longer shipped; migration handled by `migrate-di`).
3. New templates: `wiring.py.jinja2`, `usecases/__init__.py.jinja2`.
4. `pyproject_toml.jinja2`: replace `dependency-injector==4.49.1` with `wireup==2.13.0`; add `scaffold_version = "{{ scaffold_version }}"` in `[tool.scaffold-ca-python]`; add ruff `ASYNC` rule; disable ruff `TC` rule (keeps `Inject`/`Injected` at module scope, not under `TYPE_CHECKING`); add `asyncio_mode = "auto"` to pytest; add `mypy` to the `dev` group.
5. `config.py.jinja2`: keep only ENV and LOG_LEVEL (MCP still appends HOST/PORT via the existing anchor).

**Tests first**:
- `test_generate_project_creates_wiring`: `ca` produces `application/config/wiring.py` and `application/config/usecases/__init__.py`.
- `test_generate_project_no_containers`: `ca` does NOT produce `*_container.py` or `container.py`.
- `test_generate_project_pyproject_wireup`: `pyproject.toml` contains `wireup==2.13.0`, not `dependency-injector`.
- `test_generate_project_ruff_async_rule`: generated `pyproject.toml` has `ASYNC` in ruff rules and asyncio_mode.
- Update `dry_run_baseline.json` to reflect new file layout.

---

### Block C — `generate-use-case` with `--uses`

**Files**: `commands/generate_use_case.py`, `factory/simple/use_case_factory.py`, `factory/simple/delete_module_factory.py`, new templates

**Changes**:
1. Add `--uses` option: comma-separated list of gateway names. Each name is validated against `domain/model/*/gateways/<name>.py`; if it matches a helper or adapter path instead, exit with the infrastructure-only hint.
2. `UseCaseFactory`: when `--uses` is provided, render typed constructor params in `use_case.py.jinja2` and create `application/config/usecases/<snake_name>.py` from `use_case_factory.py.jinja2`.
3. Without `--uses`: generate use-case class with empty `__init__` + factory stub.
4. `DeleteModuleFactory`: detect and delete the corresponding factory file.
5. New templates: `use_case/use_case_factory.py.jinja2`.

**Tests first**:
- `test_guc_uses_creates_factory_file`: factory file at `application/config/usecases/create_order.py`.
- `test_guc_uses_typed_constructor`: generated use-case class has typed `__init__` params.
- `test_guc_uses_helper_rejected`: gateway name resolving to a helper exits non-zero with correct hint.
- `test_guc_uses_nonexistent_gateway_rejected`: unknown name exits non-zero.
- `test_guc_without_uses_valid`: without `--uses`, ruff+mypy pass.
- `test_delete_module_removes_factory`: `dm` also deletes the factory file.

---

### Block D — Driven adapters and helpers

**Files**: `factory/driven_adapters/da_*.py`, `factory/simple/helper_factory.py`, plus templates

**Changes**:
1. `da_generic.py`: append `@injectable` (or `@injectable(as_type=<Gateway>)` when `--gateway` is given) to the adapter template.
2. `da_rest_consumer.py`: new templates `rest_consumer_config.py.jinja2` (async `yield` for `httpx.AsyncClient`) and `RestConsumerSettings` with `env_prefix`; remove the per-call `async with httpx.AsyncClient`.
3. `da_secrets.py`: `SecretsSettings` with `env_prefix`.
4. `HelperFactory`: `@injectable` + docstring in template.
5. All new adapter/helper dependencies use `~=`.

**Tests first**:
- `test_gda_generic_has_injectable`: generated `adapter.py` contains `@injectable`.
- `test_gda_generic_gateway_has_as_type`: with `--gateway`, `@injectable(as_type=...)`.
- `test_gda_rest_consumer_has_settings`: `RestConsumerSettings` in generated files, no default on `base_url`.
- `test_gda_rest_consumer_has_config_file`: `rest_consumer_config.py` with async `yield`.
- `test_gh_has_injectable`: generated helper has `@injectable`.
- `test_gh_docstring_mentions_infra_only`: helper docstring warns about infrastructure scope.

---

### Block E — Entry points

**Files**: factory `ep_*.py` and all entry-point templates

**Changes**:
1. **restapi**: `wireup.integration.fastapi.setup(container, app)` in `app.py`; `lifespan` warms up resources; `rest_controller` uses `Injected[...]` with a commented example; test template shows `container.override.injectable`.
2. **mcp**: `inject_from_container(container)(bind_fn)(mcp)` in `app.py`; `tools.py`, `prompts.py`, `resources.py` use `Injected[...]`, no `@inject`, no `container.wire`.
3. **agent**: new `agent_app.py.jinja2` with `async with create_agent()`; fix `entrypoint_main.py` to import a function that exists; fix class name to PascalCase from snake-cased project name.
4. **generic**: same pattern as agent.
5. `add_mcp_tool.py`: tool stub uses `Injected[...]`.
6. Each factory calls `require_wireup_project(project_ctx)` for project-modifying commands; no legacy template routing needed.

**Tests first**:
- `test_ep_restapi_no_container_import`: generated `rest_controller.py` contains no `from application` import.
- `test_ep_restapi_uses_injected`: contains `Injected[`.
- `test_ep_mcp_uses_inject_from_container`: `app.py` contains `inject_from_container`.
- `test_ep_agent_class_name_pascalcase`: for project `my-app` generates `MyAppAgent`.
- `test_ep_agent_main_imports_existing_function`: `main.py` does not import `run`.
- `test_ep_generic_main_imports_existing_function`: same for generic.
- `test_add_mcp_tool_wireup_stub`: stub uses `Injected[...]`.
- `test_ep_legacy_project_refused`: a legacy project (no `scaffold_version`) causes `gep` to exit 1 with a message naming `migrate-di`.
- End-to-end: generate project + all entry-point types → `uv sync && ruff && mypy --strict && pytest && scaffold vs` (skip if `uv sync` fails, following existing pattern).

---

### Block F — `scaffold migrate-di` (codemod)

**Files**: `commands/migrate_di.py` (new), `core/migrations/di_wireup.py` (new), `cli.py`

**Changes**:
1. Register `migrate-di` in `cli.py` with alias `mdi`.
2. `migrate_di.py`: preconditions (git clean tree check), `--dry-run`, `--yes`, `--report json`, `--install-skill`, `--target`, `--force`.
3. `di_wireup.py`: libcst-based transforms for all FR-023 transformations:
   - `pyproject.toml` update (reuse `core/pyproject_writer.py`)
   - container → factory codemods
   - `@injectable` / `@injectable(as_type=...)` insertion
   - `Provide[...]` → `Injected[...]` conversion
   - composition-root template match and replace
4. Exit codes: 0 = no changes needed, 1 = applied with no pending, 2 = applied with pending, 3 = precondition failure, 4 = post-verification failure.
5. `--install-skill`: copy from `scaffold_ca_python/skills/migrate-di/` using `importlib.resources`; respect `--target`, `--dry-run`, `--force`.

**Tests first**:
- `test_migrate_di_requires_clean_tree`: dirty tree → exit 3 with hint.
- `test_migrate_di_dry_run_no_writes`: checksum before == after.
- `test_migrate_di_idempotent`: running twice → exit 0, no changes.
- `test_migrate_di_transforms_pyproject`: `wireup` in deps, `scaffold_version = "<installed version>"` in tool section.
- `test_migrate_di_transforms_containers`: container file → factory files.
- `test_migrate_di_factory_provider_to_transient`: `Factory` → `lifetime="transient"`.
- `test_migrate_di_injectable_on_adapter`: adapter that inherits from gateway ABC gets `as_type`.
- `test_migrate_di_provide_to_injected`: `= Depends(Provide[...])` → `Injected[...]`.
- `test_migrate_di_report_json_schema`: output matches the schema in contracts.
- `test_migrate_di_install_skill_all_targets`: creates three skill dirs + AGENTS.md line.
- `test_migrate_di_install_skill_no_overwrite`: without `--force` does not overwrite.
- Golden test: apply to `tests/fixtures/legacy_project_050/` → match snapshot.

---

### Block G — Documentation

**Files**: `docs/migration/dependency-injector-to-wireup.md`, `README.md`, template project README, spec notes in 006, 008, 019

**Changes**:
1. Migration guide with before/after for every artefact type; table of lifecycle equivalences; error reference; checklist; rollback.
2. `README.md`: updated command sections for `ca`, `guc` (with `--uses`), `gda`, `gh`, `gep`, `dm`, and new `migrate-di`.
3. Template `README.md` for generated projects: injectable scope rules (D7), adapter-with-resource convention (D6), async-to-sync bridge (`asyncio.to_thread`), `scoped` lifecycle (documented, not generated).
4. Notes in `specs/006`, `specs/008`, `specs/019` plan/spec files that spec 028 supersedes those sections.

---

### Block H — Agent migration skill

**Files**: `src/scaffold_ca_python/skills/migrate-di/` (new), `pyproject.toml` (wheel include)

**Changes**:
1. `SKILL.md`: 10-step flow covering preconditions, dry-run diagnosis, apply-with-approval, resolve-pending, arch rules (D2/D7), verification, stop conditions, rollback, and commit gate.
2. `references/recipes.md`: before/after code block per `kind` value.
3. `references/errors.md`: wireup error messages, causes, and fixes.
4. `references/checklist.md`: final verification checklist.
5. `pyproject.toml` of scaffolder: add `package-data` include for `skills/migrate-di/**`.
6. Alignment test: every `kind` in `migrate-di --report json` has a recipe key and a guide section.

---

## Appendix: Key Decisions from Research

See [research.md](research.md) for full details. Highlights:

| Decision | Choice | Reason |
|----------|--------|--------|
| DI library | wireup 2.13.0 | Async-native, validates graph at creation, typed injection, no domain imports |
| Factory placement | one file per use case in `application/config/usecases/` | No markers, no `insert_after`, `delete-module` just deletes a file |
| Adapter config | `<Name>Settings(BaseSettings)` | Type-safe, mypy-verified, pydantic-settings validates at startup |
| Codemod library | libcst | Preserves formatting and comments; used by `bump-pydantic` for the same pattern |
| Migration exit codes | 0/1/2/3/4 | Agent skill uses codes to decide next action without parsing output |
| Skill packaging | inside wheel | Skill version always matches scaffolder version |
