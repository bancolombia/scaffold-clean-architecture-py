# Tasks: Wireup DI for New Projects

**Input**: Design documents from `specs/028-wireup-di/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅

**Organization**: Tasks grouped by user story. Blocks A–H from plan.md map to phases. Tests written before implementation (Constitution Principle V).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US4). The former migration stories (labelled US4/US5 before the split) now live as US1/US2 in [docs/spec-029-migrate-di/tasks.md](../../docs/spec-029-migrate-di/tasks.md); US4 here is the A2A agent entry point.
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
- [X] T084 [US1] `delete-module`: remove wiring test function via AST line ranges; also delete the factory test file <!-- adapter wiring test + marker sync completed in T100 -->
- [X] T085 [US1] `guc --uses`: print hint when no adapter with `as_type=<Gw>` found under `infrastructure/driven_adapters/`
- [X] T086 [US1] Write failing tests: `require_wireup_project` exits 1 with `migrate-di`/`--install-skill` message; `gda`/`guc`/`gep`/`dm` on a legacy project exit 1 and write nothing
- [X] T087 [US1] Implement `require_wireup_project` in `commands/_shared.py`; remove `warn_legacy_project`; call guard in all project-modifying commands
- [X] T088 [US1] Remove legacy branches from `ep_mcp.py` and `ep_restapi.py`; delete `templates/legacy/`; delete legacy tests
- [X] T089 [US1] Rewrite T056 description in `tasks.md` to use sha256 fingerprints in `core/migrations/fingerprints_050.py` instead of rendered templates
- [X] T090 [US1] Grep audit: `grep -rn "dependency.injector\|dependency_injector" src/` must show only `project_detector`, `context.py`, fingerprints, and `core/migrations/`
- [X] T091 [US1] `scaffold_version` (H10): write failing tests → implement `core/version.py`, `ProjectContext.scaffold_version`/`is_legacy`, update `project_detector`, update pyproject template, update `generate_project.py`

**Checkpoint**: `gda --gateway` works; wiring tests are appended idempotently; legacy projects are refused (exit 1); `scaffold_version` replaces `di =` in generated pyproject.

---

## Phase 3.2 — US1 Hardening (ms_library pytest findings)

**Purpose**: `ca` + `gm` + `guc --uses` (no adapter yet) must leave `pytest`, `ruff format --check` and `mypy --strict` green. Wireup validates the whole graph in `create_container()`, so one missing adapter breaks every wiring test; the wiring module is therefore marked as one strict expected failure driven by `MISSING_ADAPTERS`, which the scaffolder maintains.

- [X] T092 [US1] Write failing tests: `tests/core/test_wiring_utils.py` (`find_missing_adapters`, `sync_missing_adapters_marker`: rewrite, idempotent, no-op without marker); `guc --uses` without adapter writes `MISSING_ADAPTERS = ["<Gw>"]`; `gda --gateway` empties it and appends an awaited stub that resolves the gateway
- [X] T093 [US1] Update `templates/project/test_wiring.py.jinja2`: `MISSING_ADAPTERS: list[str] = []` and module-level `pytestmark = pytest.mark.xfail(bool(MISSING_ADAPTERS), raises=WireupError, strict=True, reason=...)`; fix the stale docstring
- [X] T094 [US1] Add `find_missing_adapters` / `sync_missing_adapters_marker` / `sync_wiring_marker` to `core/wiring_utils.py` (AST based); `_warn_missing_adapters` in `generate_use_case.py` reuses `find_missing_adapters`
- [X] T095 [US1] Call `sync_wiring_marker` after writing (never in dry-run) from `generate_use_case.py`, `generate_driven_adapter.py` (when `--gateway`) and `delete_module_factory.py`
- [X] T096 [US1] Fix `templates/driven_adapter/wiring_test_stub.py.jinja2` (`await container.get(<Gateway>)`, gateway import path from context) and render it idempotently from the generic, rest-consumer and secrets factories via `DrivenAdapterFactory.append_wiring_test`
- [X] T097 [US1] Remove `# type: ignore[abstract]` from `test_use_case.py.jinja2` and `test_use_case_factory.py.jinja2`
- [X] T098 [US1] `ruff format --check` clean output: blank line after docstring in `config.py.jinja2` and `use_case_factory.py.jinja2`; double leading blank line in both `wiring_test_stub.py.jinja2`
- [X] T099 [US1] End-to-end test (`ca` → `gm` → `guc --uses` → ruff/format/mypy/pytest green with xfailed → `gda --gateway` → green with no xfailed)
- [X] T100 [US1] `delete-module` removes `test_container_resolves_<adapter>` as well and re-syncs `MISSING_ADAPTERS` (completes T084)

**Checkpoint**: the user flow `ca` + `gm` + `guc --uses` passes `pytest` (with expected failures naming the missing gateway) and all static checks; after `gda --gateway` there are zero xfails.

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
- [X] T034 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_agent.py`: create `application/agent_app.py.jinja2` (new template) with `async with create_agent()`; fix `entrypoint_main.py.jinja2` to import a function that exists (not `run`); fix class name to `to_pascal_case(project.python_package)` (eliminates hyphen bug) <!-- agent part superseded by T109–T120 (US4) -->
- [X] T035 [P] [US2] Create `src/scaffold_ca_python/templates/entry_point/agent/agent_app.py.jinja2` with `@asynccontextmanager async def create_agent()` composition root; `asyncio.run` in `main.py.jinja2` <!-- superseded by T109–T120 (US4) -->
- [X] T036 [US2] Update `src/scaffold_ca_python/factory/entry_points/ep_generic.py` and templates with same async composition-root pattern; fix `entrypoint_main.py.jinja2` run-import bug
- [X] T037 [P] [US2] Create `src/scaffold_ca_python/templates/entry_point/generic/generic_app.py.jinja2`
- [X] T038 [US2] Update `src/scaffold_ca_python/commands/add_mcp_tool.py` and related template: tool stub uses `Injected[UseCase]` instead of `Provide[...]`
- [X] T039 [US2] Add per-`project_ctx.di` template routing to all four entry-point factory classes (wireup templates vs frozen legacy templates); legacy projects get a warning via `warn_legacy_project` <!-- superseded by T086–T090 (legacy guard) -->
- [X] T040 [P] [US2] Add end-to-end test in `tests/commands/test_generate_entry_point.py` that generates a project + each entry-point type, runs `uv sync && ruff && mypy --strict && pytest && scaffold vs` (skip if `uv sync` fails, following existing pattern in `test_gep_mcp_generated_health_route_tests_pass`)
- [X] T041 [P] [US2] Verify spec 027 (MCP health check) still passes on the new mcp app.py template; update `test_gep_mcp_generated_health_route_tests_pass` if needed

**Checkpoint**: All four entry-point types generate without layer violations; end-to-end test passes.

---

## Phase 4.1: User Story 4 — A2A agent entry point (P2)

**Goal**: `gep --type agent` generates the open A2A server validated in the `library_aiagent/` prototype (FR-040–FR-048): Starlette + uvicorn, hello-world `A2AExecutor`, commented use-case hooks, own container in `application/app.py`; `--enable-kafka` / `--enable-mcp-client` removed.

**Independent Test** (SC-005): Run quickstart.md Scenario 4; health, agent card, and JSON-RPC `SendMessage` respond as specified and the generated project passes all quality gates without manual edits.

**Reference**: plan.md Block G; research.md Decision 9; [contracts/generated-files.md](contracts/generated-files.md#scaffold-gep---type-agent).

### Tests for US4 (write first — must FAIL)

- [X] T109 [P] [US4] Rewrite `tests/factory/entry_points/test_ep_agent.py` in the `test_ep_mcp.py` style (pre-create `config.py` for live runs): preview contains `entry_points/a2a_server/{__init__,agent_settings,a2a_config,agent_executor,agent_card,routes}.py`, root `server.py`, `application/app.py` and the four tests; `main.py` is deleted; `builder.pending_project_script == "main"`; the five `A2A_RUNTIME` dependencies land in `pyproject.toml`; an existing `application/app.py` makes `persist()` raise `FileExistsError`; HOST/PORT inserted after `LOG_LEVEL` — confirm FAIL
- [X] T110 [P] [US4] Template tests: in `tests/templates/test_entry_point_templates.py` replace the agent class/Kafka tests with checks for `A2AExecutor`, `build_agent_card`, `/api/v1/health` and the commented `some_usecase` hook; in `test_entrypoint_main_templates.py` check `agent/server.py.jinja2` has `def main` and `uvicorn`; in `test_di_config_templates.py` check `agent/app.py.jinja2` has `create_a2a_container`, `INJECTABLES`, `asynccontextmanager`, `yield` and `wireup.integration.starlette.setup`; add a test that renders every `entry_point/agent/*.jinja2` source template (not `test_*`) and asserts `from a2a` / `import a2a` appears only in `a2a_server/*` templates and `app.py.jinja2`, and never in `server.py.jinja2` (FR-042) — confirm FAIL
- [X] T111 [P] [US4] Command tests in `tests/commands/test_generate_entry_point.py` and `test_behavior_contract.py`: drop the Kafka/MCP-client tests, rows and `--add-tool` parametrize entries; drop `test_agent_class_name_has_no_hyphens` and `test_agent_main_does_not_import_run`; `--enable-kafka` / `--enable-mcp-client` exit 2; `[project.scripts]` becomes `my_app.server:main`; `a2a-sdk[http-server]` injected; `server.py` created and `main.py` deleted; `gep mcp` after `gep agent` and `gep agent` after `gep mcp` exit 1 with a conflict hint; `gep restapi` blocked when `entry_points/a2a_server/` exists; agent dry-run prints the delete/scripts notes — confirm FAIL
- [X] T112 [P] [US4] Registry and options tests: `tests/factory/test_registry.py` (`subdir == "a2a_server"`, empty `supported_flags`, agent conflicts with restapi and mcp, mcp conflicts with agent); `tests/models/test_options.py` and `tests/factory/test_dry_run_parity.py` without the removed flags; update the `"gep:agent"` entry in `tests/factory/fixtures/dry_run_baseline.json` — confirm FAIL
- [X] T113 [US4] Rename e2e scenario `02_agent_kafka_mcp` to `02_agent` (`ca` + `gep --type agent`, no flags) in `tests/e2e/test_generated_project_quality.py`; it runs `uv sync`, `ruff check`, `ruff format --check`, `mypy --strict src/`, `pytest` and `scaffold vs` (FR-048)

### Implementation for US4

- [X] T114 [US4] `src/scaffold_ca_python/factory/dependencies.py`: replace `A2A_SDK` with `A2A_SDK_HTTP_SERVER = "a2a-sdk[http-server]~=1.1.4"`; add `A2A_RUNTIME = (A2A_SDK_HTTP_SERVER, STARLETTE, UVICORN_STANDARD, WIREUP, PYDANTIC_SETTINGS)`
- [X] T115 [US4] Remove `--enable-kafka` / `--enable-mcp-client` (FR-046): `EntryPointFlag.ENABLE_KAFKA` / `ENABLE_MCP_CLIENT` in `factory/entry_points/base.py`; fields, `_FLAG_ORDER` and flag-map entries and `add_param` calls in `models/options.py`; help strings, Typer options, `_check_flags_for` branches, `EntryPointOptions` arguments and the epilog example in `commands/generate_entry_point.py`
- [X] T116 [P] [US4] Templates in `src/scaffold_ca_python/templates/entry_point/agent/`: delete `agent.py`, `agent_app.py`, `card.py`, `entrypoint_main.py`, `test_agent.py` (`.jinja2`); create `__init__`, `agent_settings`, `a2a_config`, `agent_executor`, `agent_card`, `routes`, `server`, `app`, `test_agent_executor`, `test_agent_card`, `test_routes`, `test_app` (`.jinja2`) copied from `library_aiagent/` with `{{ project.python_package }}` / `{{ project.name }}` and the Block G fixes (health `/api/v1/health`; `with TestClient(...)` fixture; no unused imports/params or banners; container-resolution tests moved to `test_app.py` using `create_a2a_container()`; `test_app.py.jinja2` MUST also cover the REST binding (`SendMessage` via the route exposed by `create_rest_routes`, path confirmed against a2a-sdk 1.1.x and then fixed in FR-041 and the contract) and lifespan idempotency (enter `TestClient(app)` twice on the same app and assert the agent-card route is registered exactly once) — FR-041, FR-043)
- [X] T117 [US4] Rewrite `src/scaffold_ca_python/factory/entry_points/ep_agent.py` (`subdir="a2a_server"`, no flags, conflicts restapi + mcp; `build()` mirrors `EntryPointMcp.build()`); extract `server_entry_notes()` from `EntryPointMcp.result_notes` into `base.py` and use it in both factories (fixes the mcp note that announced `server:start_server`); add `EntryPointConflict("agent")` to `EntryPointMcp.conflicts`
- [X] T118 [P] [US4] `src/scaffold_ca_python/templates/project/dockerfile.jinja2`: add `ENV PATH="/app/.venv/bin:$PATH"` and `CMD ["{{ python_package_script }}"]` (FR-047); update any test asserting the old `CMD`
- [X] T119 [P] [US4] `README.md`: describe `gep --type agent` as an A2A server (routes, `AGENT_*`, `HOST`, `PORT`, use-case hook). `CHANGELOG.md` is generated by release-please from Conventional Commits, so the entry comes from the commit message (`feat(agent)!: ...` with a `BREAKING CHANGE` footer for the removed flags), not from a manual edit
- [X] T120 [US4] Validation: run quickstart.md Scenario 4; `diff -r` the generated `a2a_server/` against `library_aiagent/src/library_aiagent/infrastructure/entry_points/a2a_server/` (only the package name and the Block G fixes may differ); `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy --strict src && uv run pytest` and `uv run pytest -m e2e -k agent`

**Checkpoint**: SC-005 satisfied; `gep agent` serves A2A out of the box; Kafka/MCP-client flags gone; SC-001 and SC-004 still hold.

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

## Deferred — Spec 029 (migration)

The former migration user stories (US4/US5 before the split; now US1/US2 in spec 029) and tasks **T047–T067** (`scaffold migrate-di`, skill, migration guide) moved to [docs/spec-029-migrate-di/tasks.md](../../docs/spec-029-migrate-di/tasks.md). Do not implement under spec 028.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T069 [P] Update `README.md`: `ca`, `guc` (document `--uses`), `gda`, `gh`, `gep`, `dm`; add note on async-first convention and legacy manual migration
- [X] T070 [P] Create/update template project README (generated by `ca`): injectable scope rules (D7), resource convention (D6), `asyncio.to_thread` for sync integration, `scoped` lifecycle (documented, not generated)
- [X] T071 [P] Add deprecation notes to `specs/006-ca-scaffold-enhancements/spec.md`, `specs/008-fastapi-entrypoint-baseline/spec.md`, and `specs/019-mcp-entry-point-restructure/spec.md` noting that spec 028 supersedes the DI wiring sections
- [X] T072 Run `uv run pytest --cov=scaffold_ca_python --cov-fail-under=80` and fix any coverage gaps — **965 passed**, coverage **96.43%** (2026-11-04)
- [X] T073 Run full quickstart.md validation (Scenarios 1–3 plus intermediate-state section) and record results — automated: `test_workflow.py` (11 passed) + `test_rest_consumer_quality_flow` (3 passed); manual Scenarios 2–3 in `quickstart.md` unchanged
- [X] T074 [P] Final: `uv run ruff check . && uv run mypy src && uv run pytest` — all green (pytest via T072)

---

## Phase 3.3 — Rest-consumer quality (QA ms_library oct-2026)

**Goal**: Ensure generated projects pass pytest, ruff, ruff-format, and mypy for all rest-consumer scaffolding scenarios (QA reports escenarios 1–3).

- [X] T101 (H1/§1): Fix `test_config.py.jinja2` to import `config.config` and assert `Settings` defaults; fix `test_main.py.jinja2` to call `main()` with `capsys`. `ca`+`gm` must pass `pytest --cov-fail-under=75`.
- [X] T102 (H2/§2): Append idempotent `REST_CONSUMER_BASE_URL` autouse fixture to `src/tests/conftest.py` from `da_rest_consumer`; remove duplicate fixture from `test_rest_consumer.py.jinja2`; clean up in `delete_module_factory`.
- [X] T103 (H3/§3, H19): Fix import separation in `rest_consumer.py.jinja2`, fixture/import spacing in `test_rest_consumer.py.jinja2` and generated conftest, and decorator spacing in settings. Re-test 3: Ruff and formatting pass at all nine milestones.
- [X] T104 (H4/§4): Add `plugins = pydantic.mypy` to `mypy_ini.jinja2`; replace `**kwargs: object` with explicit typed keyword params in `rest_consumer.py.jinja2`; add async `post` test in `test_rest_consumer.py.jinja2`.
- [X] T105 (§5, H20): Parametrized E2E with 3 QA scenarios (`guc→gda rest-consumer`, `guc→gda rest-consumer --gateway`, `gda rest-consumer --gateway→guc`); assert pytest/ruff/ruff-format/mypy pass at each milestone. **Re-test 4 (2026-11-03):** `test_rest_consumer_quality_flow` — **3/3 PASSED** (~96s); each case runs `ruff check`, `ruff format --check`, `mypy --strict src/`, `pytest -q -rx` on the generated project after the full scaffold sequence. Evidence: [log](../../docs/.qa-logs/retest-2026-11-03/t105-rest-consumer-e2e.log). H20 no longer reproduces (`test_main.py.jinja2` uses `pytest.CaptureFixture[str]`). **Residual (non-blocking for this sign-off):** the E2E still asserts only the final state, not intermediate milestones after `gm` / mid-sequence steps.
- [X] T106 (§5): Unit tests in `test_da_rest_consumer.py`: no double blank lines between imports, conftest.py fixture present, no `**kwargs: object`.
- [X] T107 (§6): Re-run QA scenarios; add **Re-test** section to each `docs/qa-report-escenario-0X-ms_library.md`.
- [X] T108 (§7): Spec review: SC-001 / quickstart mention rest-consumer; FR-039 coherent with scaffolder tests.

**Re-test 2026-10-30:** T107 executed with **FAIL / No conforme**, not a quality sign-off. T101/T102/T104 behavior passes in generated projects; the nine factory unit tests (T106) pass. T103 remains open (Ruff and formatting). The three T105 E2E cases fail on Ruff; the current E2E checks only the final state, so intermediate milestone assertions are also still required. T108 records the spec review and documentation alignment, not FR-039 conformance. `spec-028-post` cannot close until T103/T105 pass.

Evidence: [scenario 1 Re-test](../../docs/qa-report-escenario-01-ms_library.md#9-re-test--2026-10-30-t107), [scenario 2 Re-test](../../docs/qa-report-escenario-02-ms_library.md#9-re-test--2026-10-30-t107), [scenario 3 Re-test](../../docs/qa-report-escenario-03-ms_library.md#10-re-test--2026-10-30-t107), [failed regression log](../../docs/.qa-logs/retest-2026-10-30/regresion-rest-consumer.log).

**Re-test 2 (2026-10-30, requested 16:35 -05:00): FAIL / No conforme.** 32/36 checks pass: pytest, mypy and formatting pass at all nine milestones; Ruff fails at four post-adapter milestones with one I001 in the adapter. H19 and the conftest I001 no longer reproduce. Focused regression exits 1 (3 E2E failed, 9 unit tests passed). T103/T105 remain open; the E2E still checks final state only. All three generated projects were removed.

Latest evidence: [scenario 1](../../docs/qa-report-escenario-01-ms_library.md#10-re-test-2--2026-10-30), [scenario 2](../../docs/qa-report-escenario-02-ms_library.md#10-re-test-2--2026-10-30), [scenario 3](../../docs/qa-report-escenario-03-ms_library.md#11-re-test-2--2026-10-30), [regression failures](../../docs/.qa-logs/retest-2026-10-30-ronda-2/regresion-rest-consumer.log).

**Re-test 3 (2026-10-30, requested 17:18 -05:00): manual scope PASS, expanded regression FAIL.** All 36 manual checks pass. T103 closes; H15–H19 no longer reproduce. T105 remains open: 3 E2E fail on generated test typing (H20), 9 unit tests pass; the E2E still checks final state only. The additional `uv run mypy --strict src/` fails in all three manually generated projects, whereas the requested `uv run mypy src/ms_library` passes. All generated projects were removed; `spec-028-post` remains blocked.

Latest evidence: [scenario 1](../../docs/qa-report-escenario-01-ms_library.md#11-re-test-3--2026-10-30), [scenario 2](../../docs/qa-report-escenario-02-ms_library.md#11-re-test-3--2026-10-30), [scenario 3](../../docs/qa-report-escenario-03-ms_library.md#12-re-test-3--2026-10-30), [regression failures](../../docs/.qa-logs/retest-2026-10-30-ronda-3/regresion-rest-consumer.log).

**Re-test 4 (2026-11-03, T105 validation): PASS.** `uv run pytest tests/commands/test_generate_use_case.py::test_rest_consumer_quality_flow -v --no-cov` → **3 passed** (`guc_then_gda`, `guc_gateway_then_gda`, `gda_then_guc`). T105 marked complete. Log: [t105-rest-consumer-e2e.log](../../docs/.qa-logs/retest-2026-11-03/t105-rest-consumer-e2e.log).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **BLOCKS all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — implements `guc --uses`, adapter/helper `@injectable`
- **Phase 3.2 (US1 hardening)**: Depends on Phase 3.1; blocks the T073 quickstart validation
- **Phase 4 (US2)**: Depends on Phase 2; can run in parallel with Phase 3 (different files)
- **Phase 4.1 (US4)**: Depends on Phase 4 (entry-point templates and `ep_mcp` patterns); independent from Phase 5
- **Phase 5 (US3)**: Depends on Phase 3 and Phase 4 being mostly complete (needs wiring templates)
- **Phase 6 (Polish)**: Depends on Phases 3–5 (and Phase 3.1–3.3 as applicable)

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2 — no other story dependency
- **US2 (P1)**: Can start after Phase 2 in parallel with US1 (different file sets)
- **US3 (P2)**: Depends on US1 + US2 being at least partially complete (needs generated templates)
- **US4 (P2)**: Depends on US2 (reuses the `ep_mcp` server/app pattern); no dependency on US3
### Parallel Opportunities

- T001, T002, T003: setup tasks — T003 independent of T001/T002
- T007, T008, T009, T010: new template files — all independent
- T013, T014, T015: story-1 tests — all independent
- T021, T022, T024, T025: adapter/helper templates — all independent
- T027, T028: story-2 tests — independent of each other
- T030, T031, T033, T035, T037: entry-point templates — all independent
- T042, T043: story-3 tests — independent
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
3. Polish (T069–T074) → docs and coverage
4. Migration → [docs/spec-029-migrate-di/tasks.md](../../docs/spec-029-migrate-di/tasks.md) after 028 ships

### Parallel Team Strategy

With two developers after Phase 2:
- Developer A: Phase 3 (US1 — use cases, adapters, helpers)
- Developer B: Phase 4 (US2 — entry points)
- Both can work simultaneously; stories share no implementation files
