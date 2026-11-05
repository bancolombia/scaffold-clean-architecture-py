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

A developer generates any entry point (`restapi`, `mcp`, `agent`, `generic`) and writes a handler that declares a use case as `Injected[CreateOrderUseCase]`. No import from the `application` layer is needed in `infrastructure`. The REST lifespan and MCP startup warm up resources before serving traffic.

**Why this priority**: Eliminating the layer violation in entry points is the architectural guarantee the tool promises. Shared priority with US-1.

**Independent Test**: Generated entry-point files must not contain any import of `Container` from `application`. `validate-structure` must report no violations.

**Acceptance Scenarios**:

1. **Given** `gep restapi` is run, **When** the generated `rest_controller.py` is inspected, **Then** it uses `Injected[UseCaseClass]` and never imports `application.Container`.
2. **Given** `gep mcp` is run, **When** `bind_tools` is inspected, **Then** it uses `inject_from_container` (not `wireup.integration.fastmcp`, which targets a different package) and parameters are `Injected[...]`.
3. **Given** `gep agent` is run, **When** the generated class name is inspected for a project named `my-app`, **Then** the class is `MyAppAgent` (PascalCase, no hyphens).
4. **Given** `gep agent` or `gep generic` is run, **When** `main.py` is inspected, **Then** it imports an existing function (not a `run` function that doesn't exist).
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

- **FR-001**: `generate-project` (`ca`) MUST generate `application/config/wiring.py` with `INJECTABLES = [driven_adapters, helpers, usecases]` and a `create_container()` function that returns a single `AsyncContainer`; it MUST NOT generate any `*_container.py` file for new (wireup) projects.
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
- **FR-010**: `generate-driven-adapter` for `rest_consumer` MUST generate a `RestConsumerSettings` class (subclass of `BaseSettings`) with `env_prefix` and no default on `base_url`; it MUST generate a `rest_consumer_config.py` with an async factory (`yield`) that creates and closes an `httpx.AsyncClient` resource, following the D6 convention.
- **FR-011**: `generate-driven-adapter` for `secrets` MUST generate a `SecretsSettings` class with `env_prefix` and relevant fields without defaults.
- **FR-012**: `generate-helper` MUST decorate the generated helper class with `@injectable`. The generated file MUST include a docstring clarifying that helpers are injectable only in driven adapters and entry points (never in use cases or domain).
- **FR-013**: Adapter and helper dependencies added by `generate-*` commands MUST use the `~=` pinning operator.

#### Entry points

- **FR-014**: All generated entry-point files MUST NOT import `Container` from `application`. Dependency injection in entry points MUST use `Injected[UseCaseClass]` (restapi, mcp) or `await container.get(UseCaseClass)` (agent, generic) only.
- **FR-015**: `generate-entry-point restapi` MUST generate an `application/app.py` using `wireup.integration.fastapi.setup(container, app)` and a `lifespan` that warms up the async container before the first request.
- **FR-016**: `generate-entry-point mcp` MUST generate MCP tool/prompt/resource binding using `inject_from_container(container)(bind_fn)(mcp)` — not `wireup.integration.fastmcp`, which targets a different third-party package.
- **FR-017**: `generate-entry-point agent` and `generate-entry-point generic` MUST generate an async composition root in `application/` (`agent_app.py`, `generic_app.py`) using `async with create_<type>()` that closes the container on exit; `main.py` MUST use `asyncio.run` and import an existing function.
- **FR-018**: The class name generated by `gep agent` MUST be valid Python (PascalCase from the snake-cased project name), not the raw project name with hyphens.
- **FR-019**: `add-mcp-tool` MUST generate tool stubs that use `Injected[UseCaseClass]` for dependency injection, consistent with the wireup entry-point templates.
- **FR-020**: All `generate-*` commands that modify an existing project MUST refuse (exit 1) when the project is legacy (i.e., `scaffold_version` key absent from `[tool.scaffold-ca-python]`). The error message MUST point developers to [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md) and MAY name the planned commands `scaffold migrate-di` and `scaffold migrate-di --install-skill`. No legacy templates are shipped in the scaffolder.

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

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (= SC-1 in plan): A project built end-to-end — `ca` + `guc --uses` + `gda --gateway` (all three types, including `rest-consumer`) + `gh` + `gep` (each type) — passes `ruff`, `ruff format --check`, `mypy --strict`, `pytest`, and `scaffold validate-structure` without any manual edit. The rest-consumer QA flows also pass pytest, Ruff, formatting, and `mypy src/<pkg>` at each intermediate milestone: `ca` + `gm`, use case before adapter (with or without gateway wiring), and adapter before use case (FR-033/FR-039).
- **SC-003** (= SC-3 in plan): A missing gateway implementation, a missing required config value, or an ambiguous wiring causes a clear error at container creation or application startup — never silently at request time.
- **SC-004**: No generated entry-point file imports `Container` from `application`; `scaffold validate-structure` reports zero layer violations in a freshly generated project.

---

## Assumptions

- Legacy projects are identified by the absence of `scaffold_version` in `[tool.scaffold-ca-python]`; upgrading them is specified in [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md), not in this spec.
- The wireup version is pinned at `==2.13.0` in the generated pyproject; the scaffolder's own factories use `~=2.13.0` (per pinning policy).
- A `scoped` (per-request) lifecycle is not generated; it may be documented as a manual pattern using wireup's `scoped` parameter.
- The DB adapter templates (`asyncpg`, `DynamoDB`, etc.) are not in scope for this spec; the D6 convention is defined and documented here so that a future spec can add them without design changes.
- Multiple entry-point types per project remain unsupported (single entry-point restriction is documented, not removed).
- The `--uses` flag on `generate-use-case` accepts only gateways. Helpers are infrastructure-only (D7); use cases that need a technical capability must model it as a domain gateway with an infrastructure adapter.
- scaffold-ca-python 0.6.0 generates no dependency-injector code for new projects.

---

## Out of Scope

- **`scaffold migrate-di`**, migration guide, agent skill, and libcst codemod → [docs/spec-029-migrate-di](../../docs/spec-029-migrate-di/README.md)
- DB adapter templates (`asyncpg`, `DynamoDB`, `SQLAlchemy`, etc.)
- Lifting the single-entry-point restriction
- Scoped (per-request) lifecycle generation

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
| I — Clean Architecture in generated projects | ✅ | All entry points use `Injected[...]`; domain stays decorator-free; `validate-structure` enforced by SC-004 |
| II — Tests first; `tests/templates/` per group | ✅ | Spec mandates tests for every command change; `test_di_config_templates.py` is rewritten |
| III — Command table and aliases | ✅ | `guc` gets `--uses`; all existing aliases preserved |
| IV — Python-first idioms (async, ruff, mypy strict) | ✅ | D2 enforces async-first; FR-003 mandates ruff ASYNC rule and asyncio_mode=auto |
| V — Test-first development, 80% coverage gate | ✅ | Tests precede implementation for each command change |
| VI — DX: dry-run, aliases, hints, help examples | ✅ | FR-005 mandates a helper-vs-gateway hint; legacy guard cites spec 029 |
| VII — Branch naming | ✅ | `feature/028-wireup-di` follows `feature/<name>` pattern |
