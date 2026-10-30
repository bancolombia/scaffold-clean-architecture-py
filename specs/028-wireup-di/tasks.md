# Tasks: Wireup DI Migration

**Input**: Design documents from `specs/028-wireup-di/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Organization**: Tasks grouped by user story. Blocks A–H from plan.md map to phases. Tests written before implementation (Constitution Principle V).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5)
- All paths relative to repo root

---

## Phase 1: Setup

**Purpose**: Scaffolder infrastructure for the wireup migration — foundational changes shared by all user stories.

- [X] T004 [P] Write tests for Block A in `tests/commands/test_generate_project.py` and `tests/core/test_project_detector.py`: `di` field defaults; legacy toml without key loads as dependency-injector; warning prints correctly — confirm tests FAIL, then implement T001–T003 <!-- superseded by T091 (scaffold_version) -->
- [X] T001 Add `di: Literal["wireup", "dependency-injector"]` field to `ProjectContext` in `src/scaffold_ca_python/models/context.py` (defaults to `"wireup"`) <!-- superseded by T091 (scaffold_version) -->
- [X] T002 Update `load_project_context` in `src/scaffold_ca_python/core/project_detector.py` to read the `di` key; if absent, return `"dependency-injector"` (legacy detection) <!-- superseded by T091 (scaffold_version) -->
- [X] T003 [P] Add `warn_legacy_project(ctx: ProjectContext)` helper in `src/scaffold_ca_python/commands/_shared.py` that prints a Rich-formatted warning pointing to `scaffold migrate-di`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Wire the `di` field into every factory and command that must choose between wireup and legacy template sets. No user-story work can begin until this phase is complete.

**⚠️ CRITICAL**: Blocks B–H all depend on `project_ctx.di` being available.

- [X] T011 Write tests for Foundational block in `tests/commands/test_generate_project.py`: no `*_container.py` generated; `wiring.py` and `usecases/__init__.py` exist; pyproject contains `wireup==2.13.0`; ruff ASYNC rule present; `asyncio_mode = "auto"` present — confirm tests FAIL, then implement T005–T010
- [X] T005 Update `src/scaffold_ca_python/commands/generate_project.py`: replace `_DI_CONFIG_FILES` tuple (the four `*_container.py` entries) with `("__init__.py", "config.py", "wiring.py", "usecases/__init__.py")` for wireup projects; route legacy projects to `templates/legacy/dependency_injector/` <!-- superseded by T086–T090 (legacy guard) -->
- [X] T006 Move `container.py.jinja2`, `resource_container.py.jinja2`, `driven_adapters_container.py.jinja2`, `usecases_container.py.jinja2` to `src/scaffold_ca_python/templates/legacy/dependency_injector/` (frozen; do not correct) <!-- superseded by T086–T090 (legacy guard) -->
- [X] T007 [P] Create `src/scaffold_ca_python/templates/project/application/config/wiring.py.jinja2` with `INJECTABLES`, `create_container()` async, and correct import structure
- [X] T008 [P] Create `src/scaffold_ca_python/templates/project/application/config/usecases/__init__.py.jinja2` (empty package marker)
- [X] T009 Update `src/scaffold_ca_python/templates/project/pyproject_toml.jinja2`: replace `dependency-injector==4.49.1` with `wireup==2.13.0`; add `di = "wireup"` in `[tool.scaffold-ca-python]`; add ruff `extend-select = ["ASYNC"]` and `extend-ignore = ["TC"]`; add `asyncio_mode = "auto"` to pytest section <!-- superseded by T091 (scaffold_version) -->
- [X] T010 [P] Update `src/scaffold_ca_python/templates/project/application/config/config.py.jinja2` to contain only ENV and LOG_LEVEL (MCP HOST/PORT anchor unchanged)
- [X] T011.5 [P] Write tests asserting that `gda`, `gep`, and `guc` on a legacy project (di key absent from toml) route to frozen template paths and call `warn_legacy_project` — confirm tests FAIL before T039 <!-- superseded by T086–T090 (legacy guard) -->
- [X] T012 Update `tests/factory/fixtures/dry_run_baseline.json` to reflect new wireup file layout (alphabetical order; remove container paths; add wiring/usecases paths)

**Checkpoint**: Foundation ready — `generate-project` produces wireup projects; legacy projects still get old templates with a warning.

---

## Phase 3: User Story 1 — New project with wired use cases from day one (P1) 🎯 MVP

**Goal**: A developer can build a complete project end-to-end (`ca` + `guc --uses` + `gda` + `gh` + `gep`) and have it pass all quality checks without a single manual DI edit.

**Independent Test** (SC-001): Run quickstart.md Scenario 1 in `/tmp`; all five checks (`uv sync`, `ruff`, `mypy --strict`, `pytest`, `scaffold vs`) pass.

### Tests for US1 (write first — must FAIL before implementation)

- [X] T013 [P] [US1] Write tests in `tests/commands/test_generate_use_case.py`: `guc --uses order_repository` creates `application/config/usecases/create_order_usecase.py`; factory has typed params; without `--uses` passes ruff+mypy; gateway not found → exit non-zero; helper name → exit non-zero with infra-only hint — confirm FAIL
- [X] T014 [P] [US1] Write tests in `tests/factory/entry_points/test_ep_restapi.py` and `test_ep_mcp.py`: update expected dependency lists (`wireup~=` replaces `dependency-injector`); generated files list matches new contract — confirm FAIL
- [X] T015 [P] [US1] Write tests in `tests/templates/test_di_config_templates.py`: rewrite entirely for `wiring.py`/`usecases/` structure; assert no `DependenciesContainer`, no `UseCaseContainer`; assert `INJECTABLES`, `create_container`, `create_async_container` present — confirm FAIL

### Implementation for US1

- [X] T016 [US1] Update `src/scaffold_ca_python/commands/generate_use_case.py`: add `--uses` option (comma-separated gateway names); validate each name against `domain/model/*/gateways/`; if name matches helper or adapter path, exit non-zero with "helpers are infrastructure-only" hint
- [X] T017 [US1] Update `src/scaffold_ca_python/factory/simple/use_case_factory.py`: when `--uses` is provided, render typed constructor in `use_case.py.jinja2` and add the factory file at `application/config/usecases/<snake_name>.py` via `ModuleBuilder.add_file`; without `--uses`, generate only the use-case class (no factory file)
- [X] T018 [P] [US1] Create `src/scaffold_ca_python/templates/use_case/use_case_factory.py.jinja2` with `@injectable`-decorated factory function and correct typed params from `--uses`
- [X] T019 [P] [US1] Update `src/scaffold_ca_python/templates/use_case/use_case.py.jinja2` to render typed `__init__` parameters when `gateways` context variable is non-empty
- [X] T020 [US1] Update `src/scaffold_ca_python/factory/simple/delete_module_factory.py`: detect and add deletion of `application/config/usecases/<snake_name>.py` when deleting a use case
- [X] T026 [US1] Write tests for Block D in `tests/factory/driven_adapters/test_da_generic.py`, `test_da_rest_consumer.py`, `test_da_secrets.py` and `tests/factory/simple/test_helper_factory.py`: `@injectable` present; `RestConsumerSettings` no default on `base_url`; config file with `yield`; helper docstring warns infra-only — confirm tests FAIL, then implement T021–T025
- [X] T021 [P] [US1] Update `src/scaffold_ca_python/factory/driven_adapters/da_generic.py` and `src/scaffold_ca_python/templates/driven_adapter/generic/adapter.py.jinja2`: add `@injectable` (or `@injectable(as_type=<Gateway>)` when `--gateway` is provided) <!-- H5: re-implemented in T083 -->
- [X] T022 [P] [US1] Update `src/scaffold_ca_python/factory/simple/helper_factory.py` and `src/scaffold_ca_python/templates/helper/helper.py.jinja2`: add `@injectable`; add docstring clarifying helpers are infrastructure-only (never in use cases or domain)
- [X] T023 [US1] Update `src/scaffold_ca_python/factory/driven_adapters/da_rest_consumer.py`: generate `<name>_settings.py` (`RestConsumerSettings(BaseSettings)` with `env_prefix`, no default on `base_url`) and `<name>_config.py` (async `yield` `httpx.AsyncClient`); remove per-call `async with httpx.AsyncClient`
- [X] T024 [P] [US1] Create `src/scaffold_ca_python/templates/driven_adapter/rest_consumer/rest_consumer_settings.py.jinja2` and `rest_consumer_config.py.jinja2`; update `rest_consumer.py.jinja2` with `@injectable(as_type=...)` when gateway provided
- [X] T025 [P] [US1] Update `src/scaffold_ca_python/factory/driven_adapters/da_secrets.py` and `src/scaffold_ca_python/templates/driven_adapter/secrets/secrets_adapter.py.jinja2`: add `SecretsSettings(BaseSettings)` with `env_prefix`; add `@injectable`

**Checkpoint**: `scaffold ca` + `guc --uses` + `gda` (3 types) + `gh` produces a project that passes ruff, mypy, pytest, and validate-structure.

---

## Phase 3.1 — US1 Hardening (ms_library findings)

**Purpose**: Fix quality issues discovered by running ruff + pytest on a generated project (`ms_library`). Adds wiring tests, gda --gateway, legacy guard, and scaffold_version.

- [X] T075 [US1] Write failing tests in `tests/commands/test_generate_use_case.py`: generated test uses `_Fake<Gw>` stubs; factory import order; factory test exists; `test_wiring.py` idempotency; `gda` hint printed
- [X] T076 [US1] Write failing tests in `tests/commands/test_generate_project.py`: `ca` generates 3 new test files; pyproject has `mypy==` in dev group; pyproject has `scaffold_version =` and NOT `di =`
- [X] T077 [US1] Write failing tests in `tests/factory/driven_adapters/test_da_generic.py` (and rest_consumer/secrets): `--gateway book_repository` → `@wireup.injectable(as_type=BookRepository)`, adapter inherits gateway, correct import; unknown gateway → exit ≠ 0; appends to `test_wiring.py`
- [X] T078 [US1] Fix `templates/use_case/use_case_factory.py.jinja2` blank-line spacing; sort gateways by full module path in `factory/simple/use_case_factory.py`
- [X] T079 [US1] Fix `templates/use_case/test_use_case.py.jinja2`: generate `_Fake<Gw>` stubs and pass them; remove `@pytest.mark.asyncio` from use-case, agent, and generic test templates
- [X] T080 [US1] Add `templates/use_case/test_use_case_factory.py.jinja2`; render it from `factory/simple/use_case_factory.py` when gateways are present
- [X] T081 [US1] Add `ca` templates: `test_config.py.jinja2`, `test_wiring.py.jinja2`, `test_main.py.jinja2`; register in `commands/generate_project.py`; add `mypy==<pin>` to `dev` group in `templates/project/pyproject_toml.jinja2`
- [X] T082 [US1] Implement wiring-test append via `ModuleBuilder.append_to_file` with AST idempotency; add stub templates `templates/use_case/wiring_test_stub.py.jinja2` and `templates/driven_adapter/wiring_test_stub.py.jinja2`
- [X] T083 [US1] Implement `gda --gateway`: add CLI option, move `_find_gateway` to `commands/_shared.py`, add `gateway` context to adapter factories, update adapter templates with `{% if gateway %}` blocks for `@injectable(as_type=...)` and class inheritance; re-mark T021 `[X]`
- [ ] T084 [US1] `delete-module`: remove wiring test function via AST line ranges; also delete the factory test file
- [X] T085 [US1] `guc --uses`: print hint when no adapter with `as_type=<Gw>` found under `infrastructure/driven_adapters/`
- [X] T086 [US1] Write failing tests: `require_wireup_project` exits 1 with `migrate-di`/`--install-skill` message; `gda`/`guc`/`gep`/`dm` on a legacy project exit 1 and write nothing
- [X] T087 [US1] Implement `require_wireup_project` in `commands/_shared.py`; remove `warn_legacy_project`; call guard in all project-modifying commands
- [X] T088 [US1] Remove legacy branches from `ep_mcp.py` and `ep_restapi.py`; delete `templates/legacy/`; delete legacy tests
- [ ] T089 [US1] Rewrite T056 description in `tasks.md` to use sha256 fingerprints in `core/migrations/fingerprints_050.py` instead of rendered templates
- [X] T090 [US1] Grep audit: `grep -rn "dependency.injector\|dependency_injector" src/` must show only `project_detector`, `context.py`, fingerprints, and `core/migrations/`
- [X] T091 [US1] `scaffold_version` (H10): write failing tests → implement `core/version.py`, `ProjectContext.scaffold_version`/`is_legacy`, update `project_detector`, update pyproject template, update `generate_project.py`

**Checkpoint**: `gda --gateway` works; wiring tests are appended idempotently; legacy projects are refused (exit 1); `scaffold_version` replaces `di =` in generated pyproject.

---

## Phase 4: User Story 2 — Entry points without layer violations (P1)

**Goal**: All four entry-point types use `Injected[T]` or `container.get(T)`; no entry point imports `Container` from `application`; `validate-structure` reports zero violations.

**Independent Test** (SC-004): Run quickstart.md Scenario 2; `grep -r "from.*application.*Container" src/` returns nothing.

### Tests for US2 (write first — must FAIL)

- [X] T027 [P] [US2] Write tests in `tests/commands/test_generate_entry_point.py`: restapi controller has no `from application` import and contains `Injected[`; mcp `app.py` uses `inject_from_container` (not `wireup.integration.fastmcp`); agent class name is PascalCase for hyphenated project; agent and generic `main.py` do not import `run` — confirm FAIL
- [X] T028 [P] [US2] Write tests in `tests/commands/test_add_mcp_tool.py`: stub uses `Injected[...]`, no `@inject`, no `Provide[` — confirm FAIL

### Implementation for US2

- [X] T029 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_restapi.py` and `src/scaffold_ca_python/templates/entry_point/restapi/app.py.jinja2`: use `wireup.integration.fastapi.setup(container, app)` and a `lifespan` that calls `await container.get(...)` to warm up resources before first request; update dependency from `dependency-injector~=4.49.1` to `wireup~=2.13.0`
- [X] T030 [P] [US2] Update `src/scaffold_ca_python/templates/entry_point/restapi/rest_controller.py.jinja2`: inject with `Injected[UseCaseClass]` (commented example); remove `Provide[Container...]`
- [X] T031 [P] [US2] Update `src/scaffold_ca_python/templates/entry_point/restapi/test_rest_controller.py.jinja2`: show `container.override.injectable(target=..., new=...)` pattern
- [X] T032 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_mcp.py` and `src/scaffold_ca_python/templates/entry_point/mcp/app.py.jinja2`: use `inject_from_container(container)(bind_fn)(mcp)`; close container in async context manager
- [X] T033 [P] [US2] Update `src/scaffold_ca_python/templates/entry_point/mcp/tools.py.jinja2`, `prompts.py.jinja2`, `resources.py.jinja2`: use `Injected[...]`; remove `@inject`, `Provide[...]`, and `container.wire()`
- [X] T034 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_agent.py`: create `application/agent_app.py.jinja2` (new template) with `async with create_agent()`; fix `entrypoint_main.py.jinja2` to import a function that exists (not `run`); fix class name to `to_pascal_case(project.python_package)` (eliminates hyphen bug)
- [X] T035 [P] [US2] Create `src/scaffold_ca_python/templates/entry_point/agent/agent_app.py.jinja2` with `@asynccontextmanager async def create_agent()` composition root; `asyncio.run` in `main.py.jinja2`
- [X] T036 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_generic.py` and templates with same async composition-root pattern; fix `entrypoint_main.py.jinja2` run-import bug
- [X] T037 [P] [US2] Create `src/scaffold_ca_python/templates/entry_point/generic/generic_app.py.jinja2`
- [X] T038 [US2] Update `src/scaffold_ca_python/commands/add_mcp_tool.py` and related template: tool stub uses `Injected[UseCase]` instead of `Provide[...]`
- [X] T039 [US2] Add per-`project_ctx.di` template routing to all four entry-point factory classes (wireup templates vs frozen legacy templates); legacy projects get a warning via `warn_legacy_project` <!-- superseded by T086–T090 (legacy guard) -->
- [X] T040 [P] [US2] Add end-to-end test in `tests/commands/test_generate_entry_point.py` that generates a project + each entry-point type, runs `uv sync && ruff && mypy --strict && pytest && scaffold vs` (skip if `uv sync` fails, following existing pattern in `test_gep_mcp_generated_health_route_tests_pass`)
- [X] T041 [P] [US2] Verify spec 027 (MCP health check) still passes on the new mcp app.py template; update `test_gep_mcp_generated_health_route_tests_pass` if needed

**Checkpoint**: All four entry-point types generate without layer violations; end-to-end test passes.

---

## Phase 5: User Story 3 — Fail fast on missing dependency or config (P2)

**Goal**: Wiring errors surface at container creation or startup — never silently at request time.

**Independent Test** (SC-003): Run quickstart.md Scenario 3; `WireupError` raised at `create_container()` call, not deferred.

*Note*: This story is largely delivered by wireup itself when blocks A–E are correct. These tasks harden the test coverage and ensure the generated template explicitly warms up resources.

### Tests for US3 (write first — must FAIL)

- [X] T042 [P] [US3] Write tests in `tests/templates/test_di_config_templates.py` (new section): generate a project with a use case but no adapter; assert `WireupError` raised at `create_container()` with message naming the missing dependency — confirm FAIL
- [X] T043 [P] [US3] Write tests for config-missing scenario: `<Name>Settings` with no-default field and absent env var → pydantic `ValidationError` at `Settings()` construction (before container creation) — confirm FAIL

### Implementation for US3

- [X] T044 [US3] Ensure the `lifespan` in `restapi/app.py.jinja2` (T029) calls `await container.get(key_service)` before `yield`; document in template comment that this warms up async resources and fails fast
- [X] T045 [P] [US3] Ensure `mcp_app.py.jinja2` (T032) also warms up resources in the async context manager before yielding the `FastMCP` instance
- [X] T046 [P] [US3] Add test in `tests/templates/test_di_config_templates.py`: restapi `lifespan` calls `container.get` before `yield` (static template check)

**Checkpoint**: SC-003 satisfied; missing dependency / missing config / ambiguity all fail at startup.

---

## Phase 6: User Story 4 — Migration of 0.5.0 projects (P2)

**Goal**: `scaffold migrate-di` automates ≥70% of changes for a 0.5.0 project and reports the rest with file+line.

**Independent Test** (SC-002, SC-005): quickstart.md Scenarios 4 and 5 pass; golden snapshot matches.

### Tests for US4 (write first — must FAIL)

- [ ] T047 [P] [US4] Create `tests/fixtures/legacy_project_050/` — a handcrafted 0.5.0 project fixture with containers, Provide-based entry points, providers.Resource and providers.Configuration (to cover all pending-item kinds); commit as test data. **SC-002 baseline**: after creating the fixture, count and record in a `tests/fixtures/legacy_project_050/BASELINE.md` file the total number of lines requiring change (automated + manual) so that T049 can assert `automated_lines / total_lines ≥ 0.70`
- [ ] T048 [P] [US4] Write tests in `tests/commands/test_migrate_di.py`: `--dry-run` writes nothing (checksum test reusing pattern from `test_dry_run_checksum.py`); dirty git tree → exit 3; already-migrated → exit 0 idempotent — confirm FAIL
- [ ] T049 [P] [US4] Write golden tests in `tests/commands/test_migrate_di.py`: apply `--yes` to the fixture → snapshot of output files matches `tests/fixtures/migrate_di_golden/`; `--report json` validates against schema in `contracts/migrate-di.md` — confirm FAIL
- [ ] T050 [P] [US4] Write unit tests for each libcst transform in `tests/core/test_di_wireup_transforms.py`: pyproject update; container→factory; `@injectable` insertion; `Provide→Injected`; composition-root template match — confirm FAIL

### Implementation for US4 — Block F

- [ ] T051 [US4] Create `src/scaffold_ca_python/core/migrations/__init__.py` and `src/scaffold_ca_python/core/migrations/di_wireup.py` with libcst `MatcherDecoratableTransformer` subclasses for each transform kind (one class per kind for independent testability)
- [ ] T052 [P] [US4] Implement `pyproject_transform`: replace `dependency-injector` with `wireup`, add `di = "wireup"`, ASYNC rule, `asyncio_mode` (reuse `core/pyproject_writer.py` where possible)
- [ ] T053 [P] [US4] Implement `container_to_factory_transform`: parse `*_container.py` files with libcst; for each `providers.Singleton(Cls, ...)` emit `application/config/usecases/<snake>.py` factory; for `providers.Factory` add `lifetime="transient"`
- [ ] T054 [P] [US4] Implement `injectable_insertion_transform`: add `@injectable(as_type=<Gw>)` to adapter classes that inherit from a domain gateway ABC; add `@injectable` to helpers
- [ ] T055 [P] [US4] Implement `provide_to_injected_transform`: convert `param: T = Depends(Provide[...])` and `= Provide[...]` patterns to `param: Injected[T]`; remove `@inject` decorators; remove `from dependency_injector.wiring import ...`
- [ ] T056 [P] [US4] Implement `composition_root_transform`: compare `app.py`/`main.py` sha256 (with the python_package placeholder normalised) against the fingerprints in `src/scaffold_ca_python/core/migrations/fingerprints_050.py`; if it matches, replace with the wireup template; if not, add to pending items report (T089: legacy template files are not shipped; detection uses hashes only)
- [ ] T057 [US4] Create `src/scaffold_ca_python/commands/migrate_di.py`: CLI command with `--dry-run`, `--yes`, `--report json|text`, `--install-skill`, `--target`, `--force`; precondition checks (clean tree, legacy project); orchestrate transforms; collect pending items; run post-verification; emit exit codes 0–4 per contract
- [ ] T058 [US4] Register `migrate-di` in `src/scaffold_ca_python/cli.py` with alias `mdi`; add Rich-formatted `--help` with a usage example
- [ ] T059 [P] [US4] Create `tests/fixtures/migrate_di_golden/` — golden snapshot files of the fully-migrated fixture (auto-generated by running the transform once and committing; updated intentionally)
- [ ] T060 [US4] Implement `--install-skill` logic in `migrate_di.py` using `importlib.resources` to copy from `scaffold_ca_python/skills/migrate-di/`; respect `--target`, `--dry-run`, `--force`; create/append `AGENTS.md`

**Checkpoint**: SC-002, SC-005 satisfied; `migrate-di` automates ≥70% of 0.5.0 changes; golden tests pass.

---

## Phase 7: User Story 5 — Agent migration skill (P3)

**Goal**: A packaged skill lets AI agents follow a deterministic, safe migration flow with approval gates.

**Independent Test**: quickstart.md Scenario 6 (manual); alignment test (`test_skill_alignment.py`) passes.

### Tests for US5 (write first — must FAIL)

- [ ] T061 [P] [US5] Write `tests/templates/test_skill_alignment.py`: every `kind` value from the `migrate-di --report json` schema appears as a recipe key in `references/recipes.md` and as a section anchor in `docs/migration/dependency-injector-to-wireup.md` — confirm FAIL
- [ ] T062 [P] [US5] Write packaging test in `tests/` (or CI check): build the wheel (`uv build`) and verify `scaffold_ca_python/skills/migrate-di/SKILL.md` is present in the archive — confirm FAIL

### Implementation for US5 — Block H

- [ ] T063 [US5] Create `src/scaffold_ca_python/skills/migrate-di/SKILL.md`: 10-step flow (preconditions → dry-run diagnosis → apply-with-approval → resolve-pending → arch rules D2/D7 → verification → stop conditions → rollback → commit gate)
- [ ] T064 [P] [US5] Create `src/scaffold_ca_python/skills/migrate-di/references/recipes.md`: before/after code block for each `kind` value (resource_provider, configuration_provider, selector_provider, callable_provider, nested_container, override_in_test, usecase_uses_helper, composition_root_modified)
- [ ] T065 [P] [US5] Create `src/scaffold_ca_python/skills/migrate-di/references/errors.md`: wireup error messages (from research.md), causes, and fixes
- [ ] T066 [P] [US5] Create `src/scaffold_ca_python/skills/migrate-di/references/checklist.md`: final verification checklist (uv sync, ruff, mypy --strict, pytest, scaffold vs, AGENTS.md line present)
- [ ] T067 [US5] Update root `pyproject.toml` of the scaffolder: add `package-data` / `include` so that `scaffold_ca_python/skills/**` is included in the wheel (via hatchling `include` or `MANIFEST.in` equivalent for uv/hatchling)

**Checkpoint**: Skill packaged in wheel; alignment test passes; `--install-skill` copies all three target directories.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T068 [P] Create `docs/migration/dependency-injector-to-wireup.md`: complete guide with before/after per artefact, lifecycle equivalence table, async-first migration steps, errors+fixes section, verification checklist, rollback instructions; link from README
- [ ] T069 [P] Update `README.md`: `ca`, `guc` (document `--uses`), `gda`, `gh`, `gep`, `dm`, new `migrate-di` (with `--install-skill`); add note on async-first convention
- [ ] T070 [P] Create/update template project README (generated by `ca`): injectable scope rules (D7), resource convention (D6), `asyncio.to_thread` for sync integration, `scoped` lifecycle (documented, not generated)
- [ ] T071 [P] Add deprecation notes to `specs/006-ca-scaffold-enhancements/spec.md`, `specs/008-fastapi-entrypoint-baseline/spec.md`, and `specs/019-mcp-entry-point-restructure/spec.md` noting that spec 028 supersedes the DI wiring sections
- [ ] T072 Run `uv run pytest --cov=scaffold_ca_python --cov-fail-under=80` and fix any coverage gaps
- [ ] T073 Run full quickstart.md validation (all 6 scenarios) and record results
- [ ] T074 [P] Final: `uv run ruff check . && uv run mypy src && uv run pytest` — all green

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — implements `guc --uses`, adapter/helper `@injectable`
- **Phase 4 (US2)**: Depends on Phase 2; can run in parallel with Phase 3 (different files)
- **Phase 5 (US3)**: Depends on Phase 3 and Phase 4 being mostly complete (needs wiring templates)
- **Phase 6 (US4)**: Depends on Phase 3 and Phase 4 (migrate-di replaces what those phases generate)
- **Phase 7 (US5)**: Depends on Phase 6 (`kind` values must be final before writing recipes)
- **Phase 8 (Polish)**: Depends on all story phases

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no other story dependency
- **US2 (P1)**: Can start after Phase 2 in parallel with US1 (different file sets)
- **US3 (P2)**: Depends on US1 + US2 being at least partially complete (needs generated templates)
- **US4 (P2)**: Depends on US1 + US2 complete (migrates what they generate)
- **US5 (P3)**: Depends on US4 (needs final `kind` catalogue from migrate-di)

### Parallel Opportunities

- T001, T002, T003: setup tasks — T003 independent of T001/T002
- T007, T008, T009, T010: new template files — all independent
- T013, T014, T015: story-1 tests — all independent
- T021, T022, T024, T025: adapter/helper templates — all independent
- T027, T028: story-2 tests — independent of each other
- T030, T031, T033, T035, T037: entry-point templates — all independent
- T042, T043: story-3 tests — independent
- T047, T048, T049, T050: story-4 tests — all independent
- T052, T053, T054, T055, T056: libcst transforms — all independent (one class each)
- T063, T064, T065, T066: skill reference files — all independent

---

## Parallel Example: US1

```bash
# All these can start simultaneously once Phase 2 is complete:
T013: Write guc --uses tests (tests/commands/test_generate_use_case.py)
T014: Update ep_restapi/ep_mcp tests (tests/factory/entry_points/)
T015: Rewrite DI config template tests (tests/templates/test_di_config_templates.py)

# Then in parallel:
T016: Update generate_use_case.py command
T018: Create use_case_factory.py.jinja2
T019: Update use_case.py.jinja2
T021: Update da_generic.py + adapter.py.jinja2
T022: Update helper_factory.py + helper.py.jinja2
T024: Create rest_consumer_settings.py.jinja2 + rest_consumer_config.py.jinja2
T025: Update da_secrets.py + secrets_adapter.py.jinja2
```

---

## Implementation Strategy

### MVP: US1 + US2 (new wireup project, zero violations)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005–T012)
3. Complete Phase 3: US1 (T013–T026)
4. Complete Phase 4: US2 (T027–T041)
5. **STOP and VALIDATE**: quickstart.md Scenarios 1 + 2 pass
6. This is the shippable 0.6.0-alpha

### Incremental Delivery

1. MVP (US1+US2) → new projects work correctly
2. US3 (T042–T046) → fail-fast validation hardened
3. US4 (T047–T060) → migration path for 0.5.0 projects
4. US5 (T061–T067) → agent skill packaged
5. Polish (T068–T074) → docs and coverage

### Parallel Team Strategy

With two developers after Phase 2:
- Developer A: Phase 3 (US1 — use cases, adapters, helpers)
- Developer B: Phase 4 (US2 — entry points)
- Both can work simultaneously; stories share no implementation files
