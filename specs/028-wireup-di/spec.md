# Feature Specification: Wireup DI for New Projects

**Feature Branch**: `feature/028-wireup-di`

**Created**: 2026-10-29

**Status**: Draft

**Input**: Migrate the DI layer in scaffold-ca-python from dependency-injector to wireup (Option 3, Variant B, async-first) for **new** projects generated with 0.6.0+.

**Related (out of scope here)**: Upgrading existing 0.5.0 projects is specified in [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md) (`scaffold migrate-di`, guide, agent skill).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New project with wired use cases from day one (Priority: P1)

A developer creates a new project with `ca`, generates a use case referencing a gateway (`guc create_order --uses order_repository`), generates a driven adapter (`gda generic`), and a helper (`gh id_generator`). The project compiles, tests pass, and the container validates the dependency graph at startup — all without a single manual DI edit.

**Why this priority**: This is the core value proposition of the wireup change. If the generated scaffolding works end-to-end with zero manual wiring, developers adopt Clean Architecture without friction.

**Independent Test**: Run `ca`, `guc --uses`, `gda`, `gh`, `gep restapi`, then `uv sync && ruff && mypy --strict && pytest && scaffold vs` on the generated project — all must pass.

**Acceptance Scenarios**:

1. **Given** a new project has been generated, **When** `guc create_order --uses order_repository` is run and `order_repository` is a gateway in `domain/model/*/gateways/`, **Then** a use-case class with a typed constructor and a factory file at `application/config/usecases/create_order_usecase.py` are created.
2. **Given** `gda generic` is run, **When** the project starts, **Then** the adapter carries `@injectable` and is discovered by package scan without any central file edit.
3. **Given** a use case and adapter exist, **When** the application starts, **Then** wireup validates the full dependency graph and raises `WireupError` if any dependency is missing.
4. **Given** a helper is generated with `gh id_generator`, **When** the helper is injected in a driven adapter, **Then** it works correctly; if injected in a use case via `guc --uses id_generator`, the command rejects it with a hint.

---

### User Story 2 — Entry points receive dependencies by type without layer violations (Priority: P1)

A developer generates any entry point (`restapi`, `mcp`, `agent`, `generic`) and wires a use case into it: `Injected[CreateOrderUseCase]` in restapi and mcp handlers, constructor injection through a wireup factory in agent (`agent_executor_factory`), or `await container.get(...)` in generic. No import from the `application` layer is needed in `infrastructure`. The REST lifespan and MCP startup warm up resources before serving traffic.

**Why this priority**: Eliminating the layer violation in entry points is the architectural guarantee the tool promises. Shared priority with US-1.

**Independent Test**: Generated entry-point files must not contain any import of `Container` from `application`. `validate-structure` must report no violations.

**Acceptance Scenarios**:

1. **Given** `gep restapi` is run, **When** the generated `rest_controller.py` is inspected, **Then** it uses `Injected[UseCaseClass]` and never imports `application.Container`.
2. **Given** `gep mcp` is run, **When** `bind_tools` is inspected, **Then** it uses `inject_from_container` (not `wireup.integration.fastmcp`, which targets a different package) and parameters are `Injected[...]`.
3. **Given** `gep agent` is run, **When** `infrastructure/entry_points/a2a_server/agent_executor.py` is inspected, **Then** it imports nothing from `application`; use cases reach the executor through constructor injection (see US4 and FR-042/FR-044).
4. **Given** `gep generic` is run, **When** `main.py` is inspected, **Then** it imports an existing function (not a `run` function that doesn't exist).
5. **Given** `gep restapi` is run, **When** the app starts, **Then** the `lifespan` warms up all async resources before the first request.

---

### User Story 3 — Missing dependency or configuration detected at startup (Priority: P2)

A developer forgets to implement a gateway, misspells a config field, or has an ambiguous wiring. The error appears when the container is created or the app starts — not on the first user request.

**Why this priority**: Fail-fast behaviour is a key quality improvement over the current approach. It does not block day-one adoption (US-1/US-2) but is essential for production reliability.

**Independent Test**: Provide a project missing an adapter implementation, start it, and verify that `WireupError` is raised during container creation with a clear message.

**Acceptance Scenarios**:

1. **Given** a gateway has no implementation, **When** `create_container()` is called, **Then** wireup raises `WireupError` naming the missing dependency.
2. **Given** an adapter's `<Name>Settings` declares a field without a default, **When** the environment variable is absent, **Then** pydantic-settings raises `ValidationError` at startup before the container is even created.
3. **Given** two adapters implement the same gateway, **When** `create_container()` is called, **Then** wireup raises `WireupError` about ambiguity.

---

### User Story 4 — Agent entry point serves A2A out of the box (Priority: P2)

A developer runs `scaffold ca` and then `scaffold gep --type agent`. Running `uv run <script>` starts an A2A server (a2a-sdk, Starlette, uvicorn) that publishes its agent card and answers `Hello, World! You said: <text>` over JSON-RPC and REST, with no configuration. Commented hooks show how to inject a use case into the executor. The agent's logic (LLM, LangGraph, memory) stays in the developer's domain and driven adapters; the entry point only translates the A2A protocol.

**Why this priority**: The current `agent` output is a set of stubs that never starts a server (`run()` raises `NotImplementedError`). A working, protocol-compliant baseline is needed before any opinionated integration (Kafka, MCP client, LLM) can be layered on top. It does not block US-1/US-2.

**Independent Test**: Run quickstart.md Scenario 4 on a fresh project: the health route, the agent card and a JSON-RPC `SendMessage` call all respond as described below, and the generated project passes the quality gates without manual edits.

**Acceptance Scenarios**:

1. **Given** `ca` + `gep agent` has been run, **When** `GET /api/v1/health` is requested, **Then** it returns 200 with `{"status": "ok"}`.
2. **Given** the same project, **When** `GET /.well-known/agent-card.json` is requested, **Then** the card contains the project `name` and declares the `JSONRPC` and `HTTP+JSON` interfaces built from `AGENT_PUBLIC_URL` (default `http://localhost:8000`).
3. **Given** the same project, **When** a JSON-RPC `SendMessage` with the text `hola` and the header `A2A-Version: 1.0` is posted to `/` (or the REST equivalent to `/message:send`), **Then** the result is a `completed` task whose artifact contains `Hello, World! You said: hola`.
4. **Given** a project that already has an agent entry point, **When** `gep --type mcp` or `gep --type restapi` is run (or agent is generated after either of them), **Then** the command exits 1 with a conflict hint and writes nothing.
5. **Given** `gep --type agent --enable-kafka` or `--enable-mcp-client` is run, **When** Typer parses the options, **Then** it exits 2 with "No such option" (both flags are removed).
6. **Given** `ca` + `gep agent`, **When** `ruff check`, `ruff format --check`, `mypy --strict`, `pytest` (coverage ≥ 75 %) and `scaffold vs` are run on the generated project, **Then** all pass without any manual edit.

---

### Edge Cases

- What happens when `guc --uses` receives the name of a helper instead of a gateway? → Rejected with a clear hint: "helpers are infrastructure-only; define a gateway port in domain/model/*/gateways/ instead."
- What happens when `delete-module` removes a use case that has a factory file? → The factory file is also deleted.
- What happens when `add-mcp-tool` is called on a wireup project? → The stub uses `Injected[...]` instead of `Provide[...]`.
- What happens when a generated adapter needs an async resource (pool, HTTP client)? → The convention (D6) is followed: `<name>_config.py` with async `yield`; the composition root warms it up in `lifespan`.
- What happens when `guc --uses` is run before the corresponding `gda --gateway`? → `test_wiring.py` lists the missing gateway in `MISSING_ADAPTERS` and its tests are strict expected failures (`WireupError`), so `pytest` stays green while fail-fast is preserved (SC-3); `guc` prints a hint directing the developer to `scaffold gda`, which clears the list.

---

## Requirements *(mandatory)*

### Functional Requirements

#### DI framework replacement

- **FR-001**: `generate-project` (`ca`) MUST generate `application/config/wiring.py` with `INJECTABLES = [driven_adapters, entry_points, helpers, usecases]` and a `create_container()` function that returns a single `AsyncContainer`; it MUST NOT generate any `*_container.py` file for new (wireup) projects.
- **FR-002**: `generate-project` MUST write `scaffold_version = "<installed version>"` in the `[tool.scaffold-ca-python]` section of the generated `pyproject.toml` and set `wireup==2.13.0` as a project dependency. Absence of the `scaffold_version` key identifies a legacy (≤ 0.5.0) project.
- **FR-003**: The generated `pyproject.toml` MUST enable the `ASYNC` ruff rule and set `asyncio_mode = "auto"` in the pytest configuration.
- **FR-004**: `generate-project` MUST generate the `application/config/usecases/` package with an `__init__.py`; the package is discovered by wireup alongside `driven_adapters` and `helpers`.

#### Use cases

- **FR-005**: `generate-use-case` MUST accept an optional `--uses <gateway>[,<gateway>]` argument. Each name is validated to exist as a gateway ABC in `domain/model/*/gateways/`; if a name matches a helper or adapter instead, the command MUST exit non-zero with the message: "helpers are infrastructure-only; define a gateway port."
- **FR-006**: When `--uses` is provided, `generate-use-case` MUST generate a typed constructor in the use-case class and a factory function file at `application/config/usecases/<name>_usecase.py` that wires all declared gateways.
- **FR-007**: Without `--uses`, `generate-use-case` MUST generate the use-case class with an empty `__init__` and no factory file; the generated project MUST still pass `ruff`, `mypy --strict`, and `pytest`. (Factory files are only created when `--uses` is provided.) The generated `pyproject.toml` MUST include `mypy` in the `dev` dependency group and set `asyncio_mode = "auto"` in the pytest configuration; `@pytest.mark.asyncio` is therefore not needed in any generated test.
- **FR-008**: `delete-module` MUST delete the corresponding factory file in `application/config/usecases/` whenever it removes a use case.

#### Driven adapters and helpers

- **FR-009**: `generate-driven-adapter` MUST decorate the generated adapter class with `@injectable`. When the `--gateway` option names a gateway ABC in the domain, the decorator MUST be `@injectable(as_type=<Gateway>)`.
- **FR-010**: `generate-driven-adapter` for `rest_consumer` MUST generate a `RestConsumerSettings` class (subclass of `BaseSettings`) with `env_prefix` and no default on `base_url`; it MUST generate a `rest_consumer_config.py` with an async factory (`yield`) that creates and closes an `httpx.AsyncClient` resource, following the D6 convention. The generated `RestConsumerAdapter` MUST accept that shared `httpx.AsyncClient` via constructor injection (not open a new client per HTTP call).
- **FR-011**: `generate-driven-adapter` for `secrets` MUST generate a `SecretsSettings` class with `env_prefix` and relevant fields without defaults.
- **FR-012**: `generate-helper` MUST decorate the generated helper class with `@injectable`. The generated file MUST include a docstring clarifying that helpers are injectable only in driven adapters and entry points (never in use cases or domain).
- **FR-013**: Adapter and helper dependencies added by `generate-*` commands MUST use the `~=` pinning operator.

#### Entry points

- **FR-014**: All generated entry-point files MUST NOT import `Container` from `application`. Dependency injection in entry points MUST use `Injected[UseCaseClass]` (restapi, mcp), constructor injection through a wireup factory (agent: `agent_executor_factory` in `a2a_config.py`, see FR-044), or `await container.get(UseCaseClass)` (generic) only.
- **FR-015**: `generate-entry-point restapi` MUST generate an `application/app.py` using `wireup.integration.fastapi.setup(container, app)` and a `lifespan` that warms up the async container before the first request.
- **FR-016**: `generate-entry-point mcp` MUST generate MCP tool/prompt/resource binding using `inject_from_container(container)(bind_fn)(mcp)` — not `wireup.integration.fastmcp`, which targets a different third-party package.
- **FR-017**: `generate-entry-point generic` MUST generate an async composition root in `application/generic_app.py` using `async with create_generic()` that closes the container on exit; `main.py` MUST use `asyncio.run` and import an existing function. For `agent`, see FR-040–FR-048.
- **FR-018**: *Superseded by FR-040.* `gep agent` no longer generates a `<Pascal>Agent` class; the executor class is `A2AExecutor` and the agent name comes from `AgentSettings`.
- **FR-019**: `add-mcp-tool` MUST generate tool stubs that use `Injected[UseCaseClass]` for dependency injection, consistent with the wireup entry-point templates.
- **FR-020**: All `generate-*` commands that modify an existing project MUST refuse (exit 1) when the project is legacy (i.e., `scaffold_version` key absent from `[tool.scaffold-ca-python]`). The error message MUST point developers to [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md) and MAY name the planned commands `scaffold migrate-di` and `scaffold migrate-di --install-skill`. No legacy templates are shipped in the scaffolder.

#### A2A agent entry point (US4)

- **FR-040**: `generate-entry-point agent` MUST generate `infrastructure/entry_points/a2a_server/{__init__,agent_settings,a2a_config,agent_executor,agent_card,routes}.py`, `application/app.py`, and a package-root `server.py`, plus the tests `src/tests/application/test_app.py` and `src/tests/infrastructure/entry_points/a2a_server/{test_agent_executor,test_agent_card,test_routes}.py`. It MUST delete `main.py`, insert `HOST: str = "0.0.0.0"` and `PORT: int = 8000` after `LOG_LEVEL` in `application/config/config.py`, set `[project.scripts] <script> = "<pkg>.server:main"`, and inject `a2a-sdk[http-server]`, `starlette`, `uvicorn[standard]`, `wireup`, and `pydantic-settings`. The CLI type key stays `agent`; the package directory is `a2a_server` (protocol-named, like `mcp_server`).
- **FR-041**: The generated agent MUST run with zero configuration: `GET /api/v1/health` returns `{"status": "ok"}`; `GET /.well-known/agent-card.json` serves the card; JSON-RPC (`POST /`) and REST (`POST /message:send`) answer `SendMessage` with a completed task whose artifact is `Hello, World! You said: <text>`. Clients MUST send the `A2A-Version: 1.0` header; a2a-sdk 1.1 rejects requests without it (it assumes protocol 0.3). Every `AgentSettings` field (`env_prefix="AGENT_"`: `name`, `description`, `version`, `public_url`) MUST have a default so the server starts without a `.env` file.
- **FR-042**: `a2a` SDK imports MUST appear only in `infrastructure/entry_points/a2a_server/` and `application/app.py`. `A2AExecutor` is the anti-corruption layer: it translates user input into a use-case call and the result into A2A artifacts and task states; any exception MUST end the task in the `failed` state; `cancel` MUST raise `UnsupportedOperationError`. The scaffolder MUST NOT add agent-specific models, gateways, or response types to the domain.
- **FR-043**: `application/app.py` MUST pass the single container from `application/config/wiring.py` (`create_container()`) to `wireup.integration.starlette.setup()` (called last, after any other middleware), which closes the container on shutdown. The A2A factories are registered because `INJECTABLES` scans the whole `infrastructure/entry_points` package (FR-001); `gep agent` MUST NOT modify `wiring.py`. Modules under `entry_points/` MUST have no import-time side effects (e.g. instantiating settings that require environment variables), because the scan imports them when the container is created. The A2A protocol routes (agent card, JSON-RPC, REST) MUST be mounted in the lifespan exactly once, even if the lifespan is entered more than once.
- **FR-044**: `agent_executor.py` and `a2a_config.py` MUST include a commented example showing how to inject a use case (`some_usecase: SomeUseCase` in `agent_executor_factory` and `A2AExecutor.__init__`, and `await self._some_usecase.execute(query)` in `execute`). Uncommenting both places MUST be enough for the container to resolve the use case.
- **FR-045**: `agent` MUST conflict with `restapi` and with `mcp` in both directions (`mcp` also generates `server.py` and `application/app.py`). A conflicting `gep` MUST exit 1 with a hint and write nothing.
- **FR-046**: `generate-entry-point` MUST NOT accept `--enable-kafka` or `--enable-mcp-client`; both flags and their `EntryPointFlag` members are removed. Kafka consumers and MCP clients are future features.
- **FR-047**: The `Dockerfile` generated by `generate-project` MUST set `ENV PATH="/app/.venv/bin:$PATH"` and `CMD ["<script>"]` (the `[project.scripts]` key). This applies to every entry-point type, since the script always exists (`main:main` by default, `server:main` after `gep agent`/`mcp`).
- **FR-048**: After `ca` + `gep agent`, the generated project MUST pass `ruff check .`, `ruff format --check .`, `mypy --strict src/`, `pytest` (with the template's `--cov-fail-under=75`), and `scaffold validate-structure` without any manual edit.

#### Post-generation validation (Phase 3.1)

- **FR-031**: The test generated by `guc --uses` MUST construct the use case with one local `_Fake<Gw>` stub per gateway (a minimal concrete subclass of the gateway ABC) and pass the stubs as arguments. The generated test MUST pass `ruff check` and `mypy --strict` without any manual edit.
- **FR-032**: The import block in a generated use-case factory MUST satisfy ruff's `I` (isort) rules: stdlib/third-party imports, one blank line, then first-party imports ordered by module path. Multiple gateways from different models MUST NOT produce extra blank lines between first-party imports.
- **FR-033**: `generate-project` MUST generate `src/tests/application/config/test_config.py`, `src/tests/application/config/test_wiring.py`, and `src/tests/test_main.py`. A project created with `ca` + `gm` MUST reach the `--cov-fail-under=75` threshold without any additional manual edits, and `pytest`, `ruff format --check` and `mypy --strict` MUST pass even before any use case or adapter exists.
- **FR-039**: After `generate-driven-adapter --type rest-consumer` (with or without `--gateway`), the generated project MUST pass `ruff check .`, `ruff format --check .`, `mypy src/<pkg>`, and `pytest --cov src/<pkg>` without any manual edit. Wiring tests MUST be able to resolve the container when the adapter is wired — a test-env fixture MUST supply all required settings (aligned with D5: fail-fast at startup for missing required fields).
- **FR-034**: `guc --uses` MUST append `test_container_resolves_<name>_usecase` to `src/tests/application/config/test_wiring.py`. `gda --gateway` MUST append `test_container_resolves_<adapter>`, which awaits `container.get(<Gateway>)`. Both operations MUST be idempotent (no duplicate test function if the command is run twice). `delete-module` MUST remove the corresponding test function.
- **FR-035**: When `guc --uses <gw>` is run and no driven adapter with `as_type=<Gw>` is found under `infrastructure/driven_adapters/`, the command MUST print a hint suggesting the next step: `scaffold gda --type <type> --name <adapter> --gateway <gw>`.
- **FR-037**: The generated `test_wiring.py` MUST define `MISSING_ADAPTERS: list[str]` and a module-level `pytestmark = pytest.mark.xfail(bool(MISSING_ADAPTERS), raises=WireupError, strict=True, ...)`. `guc --uses`, `gda --gateway` and `delete-module` MUST recompute the list (gateways imported by `application/config/usecases/` factories minus `as_type=` targets under `infrastructure/driven_adapters/`) and rewrite only that assignment; they MUST NOT touch it in dry-run or when it is absent.
- **FR-038**: Generated tests and sources MUST NOT contain unused `type: ignore` comments and MUST be `ruff format --check` clean.
- **FR-036**: `guc --uses` MUST generate `src/tests/application/config/usecases/test_<name>_usecase.py`, which instantiates the factory with fake adapters and asserts the returned object is the correct type.

### Key Entities

- **ProjectContext**: Extended with `scaffold_version: str | None` (read from `[tool.scaffold-ca-python].scaffold_version`; `None` if absent — legacy project) and `is_legacy: bool` (property; `True` when `scaffold_version is None`).
- **UseCase factory file**: `application/config/usecases/<snake_name>_usecase.py` — one per use case, containing a single `@injectable`-decorated factory function.
- **Adapter settings**: `<AdapterName>Settings(BaseSettings)` with `env_prefix`, living in the adapter's own package; injectable by type.
- **Resource config**: `<adapter_name>_config.py` in the adapter package; contains an async factory with `yield` for resources with a lifecycle.
- **AgentSettings**: `BaseSettings` with `env_prefix="AGENT_"` in `entry_points/a2a_server/agent_settings.py`; holds the agent identity (`name`, `description`, `version`) and `public_url`, from which the agent card interfaces are built. Injectable by type.
- **A2AExecutor**: the `a2a` `AgentExecutor` implementation in `entry_points/a2a_server/agent_executor.py`; the anti-corruption layer between the A2A protocol and the developer's use cases (FR-042).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (= SC-1 in plan): A project built end-to-end — `ca` + `guc --uses` + `gda --gateway` (all three types, including `rest-consumer`) + `gh` + `gep` (each type, including `agent` with no flags) — passes `ruff`, `ruff format --check`, `mypy --strict`, `pytest`, and `scaffold validate-structure` without any manual edit. The rest-consumer QA flows also pass pytest, Ruff, formatting, and `mypy src/<pkg>` at each intermediate milestone: `ca` + `gm`, use case before adapter (with or without gateway wiring), and adapter before use case (FR-033/FR-039).
- **SC-003** (= SC-3 in plan): A missing gateway implementation, a missing required config value, or an ambiguous wiring causes a clear error at container creation or application startup — never silently at request time.
- **SC-004**: No generated entry-point file imports `Container` from `application`; `scaffold validate-structure` reports zero layer violations in a freshly generated project.
- **SC-005**: `ca` + `gep agent` + `uv run <script>` serves the agent card and answers a JSON-RPC `SendMessage` with the hello-world artifact, without any manual edit (FR-041, FR-048).

---

## Assumptions

- Legacy projects are identified by the absence of `scaffold_version` in `[tool.scaffold-ca-python]`; upgrading them is specified in [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md), not in this spec.
- The wireup version is pinned at `==2.13.0` in the generated pyproject; the scaffolder's own factories use `~=2.13.0` (per pinning policy).
- A `scoped` (per-request) lifecycle is not generated; it may be documented as a manual pattern using wireup's `scoped` parameter.
- The DB adapter templates (`asyncpg`, `DynamoDB`, etc.) are not in scope for this spec; the D6 convention is defined and documented here so that a future spec can add them without design changes.
- Multiple entry-point types per project remain unsupported (single entry-point restriction is documented, not removed).
- The `--uses` flag on `generate-use-case` accepts only gateways. Helpers are infrastructure-only (D7); use cases that need a technical capability must model it as a domain gateway with an infrastructure adapter.
- scaffold-ca-python 0.6.0 generates no dependency-injector code for new projects.
- The agent entry point targets a2a-sdk 1.1.x: the protobuf types in `a2a.types.a2a_pb2` (`AgentCard` with `supported_interfaces`, no `url` field) and the Starlette route factories in `a2a.server.routes` (`create_agent_card_routes`, `create_jsonrpc_routes`, `create_rest_routes`). Starlette is used directly (not FastAPI) because the SDK already returns Starlette routes.
- The A2A agent was validated first as a hand-written prototype (`library_aiagent/`); the templates reproduce it with the package name substituted.

---

## Out of Scope

- **`scaffold migrate-di`**, migration guide, agent skill, and libcst codemod → [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md)
- DB adapter templates (`asyncpg`, `DynamoDB`, `SQLAlchemy`, etc.)
- Lifting the single-entry-point restriction
- Scoped (per-request) lifecycle generation
- Kafka consumers and MCP clients for the agent entry point (former `--enable-kafka` / `--enable-mcp-client`)
- Opinionated agent integrations (LangGraph, checkpointers, LLM gateways, observability); they may later be offered as optional driven adapters, never inside the entry point
- `delete-module` undoing an entry point (restoring `main.py`, `HOST`/`PORT`, or `[project.scripts]`)

---

## Partially Replaces

This spec partially replaces the following specs for the areas noted:

- **006 — Clean Architecture Scaffold Enhancements**: DI container generation
- **008 — FastAPI Entry Point Baseline Alignment**: entry-point DI wiring
- **019 — MCP Entry Point Restructure**: MCP DI wiring and composition root

---

## Constitution Check

| Principle | Status | Notes |
|-----------|--------|-------|
| I — Clean Architecture in generated projects | ✅ | All entry points use `Injected[...]` or factory injection; domain stays decorator-free; A2A imports confined to the entry point (FR-042); `validate-structure` enforced by SC-004 |
| II — Tests first; `tests/templates/` per group | ✅ | Spec mandates tests for every command change; `test_di_config_templates.py` is rewritten |
| III — Command table and aliases | ✅ | `guc` gets `--uses`; all existing aliases preserved |
| IV — Python-first idioms (async, ruff, mypy strict) | ✅ | D2 enforces async-first; FR-003 mandates ruff ASYNC rule and asyncio_mode=auto |
| V — Test-first development, 80% coverage gate | ✅ | Tests precede implementation for each command change |
| VI — DX: dry-run, aliases, hints, help examples | ✅ | FR-005 mandates a helper-vs-gateway hint; legacy guard cites spec 029; agent runs with zero configuration (FR-041) and entry-point conflicts print a hint (FR-045) |
| VII — Branch naming | ✅ | `feature/028-wireup-di` follows `feature/<name>` pattern |
