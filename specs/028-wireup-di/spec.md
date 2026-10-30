# Feature Specification: Wireup DI Migration

**Feature Branch**: `feature/028-wireup-di`

**Created**: 2026-10-29

**Status**: Draft

**Input**: Migrate the DI layer in scaffold-ca-python from dependency-injector to wireup (Option 3, Variant B, async-first).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — New project with wired use cases from day one (Priority: P1)

A developer creates a new project with `ca`, generates a use case referencing a gateway (`guc create_order --uses order_repository`), generates a driven adapter (`gda generic`), and a helper (`gh id_generator`). The project compiles, tests pass, and the container validates the dependency graph at startup — all without a single manual DI edit.

**Why this priority**: This is the core value proposition of the migration. If the generated scaffolding works end-to-end with zero manual wiring, developers adopt Clean Architecture without friction.

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

### User Story 4 — Existing 0.5.0 projects migrate to wireup with guided tooling (Priority: P2)

A developer with a project generated by scaffold-ca-python 0.5.0 runs `scaffold migrate-di --dry-run` to preview changes, then `scaffold migrate-di --yes` to apply them. The command automates what it can (pyproject, containers → factories, decorators, `Provide` → `Injected`), reports every pending manual change with file and line, and finishes by running the test suite.

**Why this priority**: Without a migration path, adopting the new version would mean rewriting projects by hand. The command lowers that barrier significantly.

**Independent Test**: Apply `migrate-di` to the 0.5.0 test fixture, verify that the output matches the golden snapshot, that `--dry-run` produces no file changes, and that after resolving the reported manual items the full suite passes.

**Acceptance Scenarios**:

1. **Given** a 0.5.0 project with a clean git tree, **When** `scaffold migrate-di --dry-run` is run, **Then** a unified diff and a list of automated changes plus pending items are printed; no file is written.
2. **Given** a 0.5.0 project, **When** `migrate-di --yes` is run, **Then** pyproject is updated, containers are replaced by factory files, adapters and helpers get `@injectable`, `Provide[...]` in entry points is converted to `Injected[...]`, and the suite is run at the end.
3. **Given** a project with an uncommitted change, **When** `migrate-di` is run without `--dry-run`, **Then** the command exits non-zero with a message asking the user to commit or stash first.
4. **Given** a 0.5.0 project, **When** `migrate-di --install-skill [--target all]` is run, **Then** the migration skill is copied to `.claude/skills/migrate-di/`, `.cursor/skills/migrate-di/`, and `.agents/skills/migrate-di/`, and a reference is appended to `AGENTS.md`.
5. **Given** a project that already has the skill installed, **When** `migrate-di --install-skill` is run without `--force`, **Then** it exits without overwriting and prints a hint to use `--force`.

---

### User Story 5 — An AI agent migrates a 0.5.0 project using the packaged skill (Priority: P3)

A developer installs the migration skill with `--install-skill` and tells an AI agent (e.g. Claude Code) "migrate this project to wireup". The agent follows the skill's step-by-step flow, applies the codemod, resolves pending items using the recipes, runs verification, and asks the developer before every commit and before applying changes.

**Why this priority**: The skill makes automation reusable and prevents agents from improvising. It is useful but not blocking; a developer can always follow the guide manually.

**Independent Test**: (Manual acceptance) Follow the skill on a fresh copy of the 0.5.0 fixture; the agent must stop to request approval before `migrate-di --yes` and before any `git commit`.

**Acceptance Scenarios**:

1. **Given** the skill is installed, **When** the agent reads `SKILL.md`, **Then** it follows preconditions (clean tree, green tests) before applying any change.
2. **Given** a pending item has a recipe in `references/recipes.md`, **When** the agent applies the recipe, **Then** the affected test passes without other changes.
3. **Given** a pending item has no recipe, **When** the agent encounters it, **Then** it stops and asks the developer instead of improvising.

---

### Edge Cases

- What happens when `guc --uses` receives the name of a helper instead of a gateway? → Rejected with a clear hint: "helpers are infrastructure-only; define a gateway port in domain/model/*/gateways/ instead."
- What happens when `delete-module` removes a use case that has a factory file? → The factory file is also deleted.
- What happens when `add-mcp-tool` is called on a wireup project? → The stub uses `Injected[...]` instead of `Provide[...]`.
- What happens when a generated adapter needs an async resource (pool, HTTP client)? → The convention (D6) is followed: `<name>_config.py` with async `yield`; the composition root warms it up in `lifespan`.
- What happens when `migrate-di` encounters a `providers.Resource` or `providers.Configuration`? → Not automatically rewritten; reported as a pending item with file, line, guide section, and a suggested `<name>_config.py` skeleton.
- What happens when `guc --uses` is run before the corresponding `gda --gateway`? → `test_wiring.py` gets a failing test stub immediately (fail-fast, SC-3), and `guc` prints a hint directing the developer to `scaffold gda`.

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
- **FR-020**: All `generate-*` commands that modify an existing project MUST refuse (exit 1) when the project is legacy (i.e., `scaffold_version` key absent from `[tool.scaffold-ca-python]`). The error message MUST name both `scaffold migrate-di` and `scaffold migrate-di --install-skill` as remediation options. No legacy templates are shipped in the scaffolder.

#### Migration command

- **FR-021**: `scaffold migrate-di` MUST refuse to run (exit non-zero) if the git working tree is not clean; the error message MUST include a git-restore hint.
- **FR-022**: `scaffold migrate-di --dry-run` MUST print a unified diff of every planned change and a list of pending manual items; it MUST NOT write any file.
- **FR-023**: `scaffold migrate-di --yes` MUST apply the following transformations automatically:
  1. Update `pyproject.toml`: change the dependency, add `scaffold_version = "<installed version>"`, enable the `ASYNC` ruff rule, set `asyncio_mode = "auto"`.
  2. Read each `*_container.py` with a libcst-based codemod and generate one `application/config/usecases/<name>.py` per `providers.Singleton` or `providers.Factory` found (`Factory` maps to `lifetime="transient"`).
  3. Add `@injectable(as_type=<Gateway>)` to adapters that inherit from a domain gateway ABC and `@injectable` to helpers.
  4. Convert `param: T = Depends(Provide[...])` and `= Provide[...]` patterns to `param: Injected[T]`; remove `@inject` decorators.
  5. Replace composition-root and `main` files only when they match the 0.5.0 rendered template byte-for-byte; otherwise, report them as pending.
  6. Delete the `*_container.py` files and write `application/config/wiring.py`.
- **FR-024**: For patterns that cannot be automatically transformed (see FR-023), `migrate-di` MUST emit a structured report (JSON with `--report json`) containing for each pending item: `kind`, `file`, `line`, `guide_section`, and a `suggested_skeleton`. The exit code MUST differ between "applied with no pending items" and "applied with pending items".
- **FR-025**: `migrate-di` MUST be idempotent: running it twice on a project that has already been migrated MUST produce no changes and exit zero.
- **FR-026**: After applying changes, `migrate-di` MUST run `uv sync`, `ruff`, `mypy --strict`, and `pytest` and print the result; it MUST NOT commit automatically.

#### Migration skill

- **FR-027**: The migration skill MUST be packaged inside the wheel at `scaffold_ca_python/skills/migrate-di/` with this structure: `SKILL.md` (step-by-step flow for the agent), `references/recipes.md`, `references/errors.md`, `references/checklist.md`.
- **FR-028**: `scaffold migrate-di --install-skill [--target claude|cursor|agents|all]` (default `all`) MUST copy the skill to `.claude/skills/migrate-di/`, `.cursor/skills/migrate-di/`, and `.agents/skills/migrate-di/` in the target project, and MUST append a reference line to `AGENTS.md` (creating it if absent). Without `--force`, it MUST NOT overwrite an existing skill.
- **FR-029**: `SKILL.md` MUST contain explicit stop conditions: the agent MUST request user approval before running `migrate-di --yes` and before any `git commit`; if a pending item has no recipe in `references/recipes.md`, the agent MUST stop and ask the user.
- **FR-030**: The set of `kind` values emitted by `migrate-di --report json` MUST be the same as the set of recipe keys in `references/recipes.md` and the section anchors in `docs/migration/dependency-injector-to-wireup.md`. A test MUST verify this alignment.

#### Post-generation validation (Phase 3.1)

- **FR-031**: The test generated by `guc --uses` MUST construct the use case with one local `_Fake<Gw>` stub per gateway (a minimal concrete subclass of the gateway ABC) and pass the stubs as arguments. The generated test MUST pass `ruff check` and `mypy --strict` without any manual edit.
- **FR-032**: The import block in a generated use-case factory MUST satisfy ruff's `I` (isort) rules: stdlib/third-party imports, one blank line, then first-party imports ordered by module path. Multiple gateways from different models MUST NOT produce extra blank lines between first-party imports.
- **FR-033**: `generate-project` MUST generate `src/tests/application/config/test_config.py`, `src/tests/application/config/test_wiring.py`, and `src/tests/test_main.py`. A project created with `ca` + `gm` + `guc` MUST reach the `--cov-fail-under=75` threshold without any additional manual edits.
- **FR-034**: `guc --uses` MUST append `test_container_resolves_<name>_usecase` to `src/tests/application/config/test_wiring.py`. `gda --gateway` MUST append `test_container_resolves_<adapter>`. Both operations MUST be idempotent (no duplicate test function if the command is run twice). `delete-module` MUST remove the corresponding test function.
- **FR-035**: When `guc --uses <gw>` is run and no driven adapter with `as_type=<Gw>` is found under `infrastructure/driven_adapters/`, the command MUST print a hint suggesting the next step: `scaffold gda --type <type> --name <adapter> --gateway <gw>`.
- **FR-036**: `guc --uses` MUST generate `src/tests/application/config/usecases/test_<name>_usecase.py`, which instantiates the factory with fake adapters and asserts the returned object is the correct type.

### Key Entities

- **ProjectContext**: Extended with `scaffold_version: str | None` (read from `[tool.scaffold-ca-python].scaffold_version`; `None` if absent — legacy project) and `is_legacy: bool` (property; `True` when `scaffold_version is None`).
- **UseCase factory file**: `application/config/usecases/<snake_name>_usecase.py` — one per use case, containing a single `@injectable`-decorated factory function.
- **Adapter settings**: `<AdapterName>Settings(BaseSettings)` with `env_prefix`, living in the adapter's own package; injectable by type.
- **Resource config**: `<adapter_name>_config.py` in the adapter package; contains an async factory with `yield` for resources with a lifecycle.
- **Migration report item**: `{kind, file, line, guide_section, suggested_skeleton}` — structured output of `migrate-di --report json`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (= SC-1 in plan): A project built end-to-end — `ca` + `guc --uses` + `gda --gateway` (all three types) + `gh` + `gep` (each type) — passes `ruff`, `mypy --strict`, `pytest`, and `scaffold validate-structure` without any manual edit.
- **SC-002** (= SC-2 in plan): `migrate-di` on the 0.5.0 test fixture automatically applies at least 70% of the total required changes (measured as changed lines vs total lines requiring change); the remainder is reported with file and line.
- **SC-003** (= SC-3 in plan): A missing gateway implementation, a missing required config value, or an ambiguous wiring causes a clear error at container creation or application startup — never silently at request time.
- **SC-004**: No generated entry-point file imports `Container` from `application`; `scaffold validate-structure` reports zero layer violations in a freshly generated project.
- **SC-005**: `migrate-di --dry-run` on any project with a clean git tree produces zero file writes (verified by checksum).
- **SC-006**: Every `kind` in `migrate-di --report json` output has a corresponding recipe in `references/recipes.md` and a section in the migration guide.

---

## Assumptions

- Projects generated with scaffold-ca-python 0.5.0 are the only legacy projects in scope; earlier versions are not supported by `migrate-di`.
- The wireup version is pinned at `==2.13.0` in the generated pyproject; the scaffolder's own factories use `~=2.13.0` (per pinning policy).
- `libcst` is added as a runtime dependency of the scaffolder (not an optional extra) because `migrate-di` is a core command, not a plugin.
- The agent migration skill targets Claude Code (`.claude/skills/`), Cursor (`.cursor/skills/`), and the generic Agent Skills spec (`.agents/skills/`); other harnesses are out of scope.
- A `scoped` (per-request) lifecycle is not generated; it is documented in the migration guide as a pattern the developer can adopt manually using wireup's `scoped` parameter.
- The DB adapter templates (`asyncpg`, `DynamoDB`, etc.) are not in scope for this spec; the D6 convention is defined and documented here so that a future spec can add them without design changes.
- Multiple entry-point types per project remain unsupported (single entry-point restriction is documented, not removed).
- The `--uses` flag on `generate-use-case` accepts only gateways. Helpers are infrastructure-only (D7); use cases that need a technical capability must model it as a domain gateway with an infrastructure adapter.
- scaffold-ca-python 0.6.0 generates no dependency-injector code; compatibility with ≤ 0.5.0 projects is handled exclusively by `scaffold migrate-di` and its skill.

---

## Out of Scope

- DB adapter templates (`asyncpg`, `DynamoDB`, `SQLAlchemy`, etc.)
- Lifting the single-entry-point restriction
- Scoped (per-request) lifecycle generation
- Migration of projects older than 0.5.0
- Support for harnesses other than Claude Code, Cursor, and Agent Skills

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
| III — Command table and aliases | ✅ | `migrate-di` gets alias `mdi`; `guc` gets `--uses`; all existing aliases preserved |
| IV — Python-first idioms (async, ruff, mypy strict) | ✅ | D2 enforces async-first; FR-003 mandates ruff ASYNC rule and asyncio_mode=auto |
| V — Test-first development, 80% coverage gate | ✅ | Bloque F and Bloque H include full test plans before implementation |
| VI — DX: dry-run, aliases, hints, help examples | ✅ | `migrate-di` supports `--dry-run`; FR-021 mandates a git-restore hint; FR-005 mandates a helper-vs-gateway hint |
| VII — Branch naming | ✅ | `feature/028-wireup-di` follows `feature/<name>` pattern |
