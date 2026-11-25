# Feature Specification: psycopg Async Driven Adapter

**Feature Branch**: `feature/031-psycopg-adapter`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "scaffold gda --type psycopg generates an async psycopg 3 driven adapter (raw SQL, no ORM) with a lazily opened connection pool, gateway support, and coexistence with other adapter types"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate psycopg Adapter (Priority: P1)

A developer whose project must talk to PostgreSQL with plain SQL — no ORM — scaffolds an async psycopg 3 adapter with a single command. The generated files pass every quality check without manual edits, and the generated tests run without a database server.

**Why this priority**: Core value — teams that are not allowed to use an ORM today have no generated option and hand-write the pool, settings and lifecycle code. Without this story the feature delivers nothing.

**Independent Test**: Run `scaffold gda --type psycopg` in a new scaffold project, then run ruff, mypy --strict, pytest and `scaffold vs`. All must pass with zero manual edits and no PostgreSQL instance available.

**Acceptance Scenarios**:

1. **Given** a scaffold project exists, **When** `scaffold gda --type psycopg` is run, **Then** four source files are created (`__init__.py`, `psycopg_settings.py`, `psycopg_config.py`, `psycopg_repository.py`) plus one test file (`test_psycopg_adapter.py`), and `psycopg[binary]`, `psycopg-pool` and `pydantic-settings` are added to the runtime dependencies.
2. **Given** the adapter was generated, **When** the project's test suite runs with no database reachable, **Then** all tests pass, because creating the dependency-injection container and resolving the repository opens no database connection.
3. **Given** the generated repository, **When** a developer reads its example query, **Then** values are passed as query parameters (`%s` placeholders) and never interpolated into the SQL string.
4. **Given** `--driver` is passed together with `--type psycopg`, **When** the command runs, **Then** it exits with code 1 and explains that `--driver` is only valid with `--type sqlalchemy`.
5. **Given** the project already has the psycopg adapter, **When** `scaffold gda --type psycopg` is run again, **Then** the command refuses because the directory exists, and the env fixture in `conftest.py` is not duplicated.
6. **Given** `--dry-run`, **When** `scaffold gda --type psycopg --dry-run` is run, **Then** the file tree and pending runtime dependencies are printed and nothing is written.

---

### User Story 2 - Gateway Integration (Priority: P1)

A developer binds the psycopg adapter to a domain gateway so dependency injection wires it into use cases automatically. The wiring test and `MISSING_ADAPTERS` reflect the binding.

**Why this priority**: Real projects reach the adapter through a gateway port; an unbound adapter is never used by the application.

**Independent Test**: Run `scaffold gm --name book`, `scaffold guc --name get_book --uses book_repository`, then `scaffold gda --type psycopg --gateway book_repository`; verify the repository implements `BookRepository`, the wiring test resolves it, and the whole suite passes.

**Acceptance Scenarios**:

1. **Given** a project with a `book_repository` gateway, **When** `scaffold gda --type psycopg --gateway book_repository` is run, **Then** the repository class is registered with `as_type=BookRepository` and inherits from `BookRepository`.
2. **Given** the adapter is generated with `--gateway`, **When** the wiring test file is inspected, **Then** it contains `test_container_resolves_psycopg`, and that test passes without a database.
3. **Given** `MISSING_ADAPTERS` listed `BookRepository` before generation, **When** the adapter is generated with `--gateway book_repository`, **Then** `BookRepository` is removed from `MISSING_ADAPTERS`.
4. **Given** `--gateway` names a gateway that does not exist, **When** the command runs, **Then** it exits with code 1 and a hint to create the model first.

---

### User Story 3 - Coexistence and Cleanup (Priority: P2)

A developer combines the psycopg adapter with `rest-consumer` and `sqlalchemy` in the same project. All adapters share one valid `conftest.py`. Deleting the psycopg adapter with `scaffold dm` removes only its own fixture.

**Why this priority**: Multi-adapter projects are common and a broken shared test configuration fails every test; cleanup completes the lifecycle but is secondary to generation.

**Independent Test**: Generate `rest-consumer`, `sqlalchemy` and `psycopg`; verify `conftest.py` parses and has a single header; run `scaffold dm --name psycopg --confirm`; verify `psycopg_env` is gone and the other fixtures remain.

**Acceptance Scenarios**:

1. **Given** a project with no adapters, **When** `rest-consumer`, `sqlalchemy` and `psycopg` are generated in sequence, **Then** `conftest.py` is valid Python with exactly one header and contains `rest_consumer_env`, `sqlalchemy_env` and `psycopg_env`.
2. **Given** a project with all three adapters, **When** `scaffold dm --name psycopg --confirm` is run, **Then** `psycopg_env` is removed and the other two fixtures remain.
3. **Given** the `sqlalchemy` adapter (PostgreSQL driver) was generated first, **When** the psycopg adapter is generated, **Then** the connection-pool dependency is still added even though the PostgreSQL driver package is already declared.

---

### Edge Cases

- `src/tests/conftest.py` does not exist → it is created with the header and the `psycopg_env` fixture.
- `psycopg[binary]` is already a dependency (from the sqlalchemy adapter) → it is not duplicated, and `psycopg-pool` is still added as a separate requirement.
- The first query runs while several requests arrive at once → the pool is opened exactly once.
- The database is unreachable at startup → the service still starts; the first query fails after at most `PSYCOPG_TIMEOUT` seconds instead of failing at container creation.
- The application shuts down before any query ran → closing the never-opened pool succeeds silently.
- The first open fails (database down) and the database comes back → the next query opens a new pool and succeeds without restarting the service.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST accept `psycopg` as a value of `scaffold gda --type` and list it in `--help` with a description and at least one usage example.
- **FR-002**: The generator MUST create four source files — `__init__.py`, `psycopg_settings.py`, `psycopg_config.py`, `psycopg_repository.py` — under `infrastructure/driven_adapters/psycopg/`.
- **FR-003**: The generator MUST create `test_psycopg_adapter.py` under `src/tests/infrastructure/driven_adapters/psycopg/`.
- **FR-004**: The generator MUST add `psycopg[binary]`, `psycopg-pool` and `pydantic-settings` to the project's runtime dependencies, each declared as its own requirement so that an existing `psycopg[binary]` entry cannot suppress `psycopg-pool`. No type-stub package is added.
- **FR-005**: `psycopg_settings.py` MUST define `PsycopgSettings` with the `PSYCOPG_` environment prefix and exactly these fields: `database_url` (required, so a missing `PSYCOPG_DATABASE_URL` fails at startup), `min_size: int = 1`, `max_size: int = 10` and `timeout: float = 30.0` (seconds). `timeout` bounds both opening the pool and waiting for a free connection.
- **FR-006**: `psycopg_config.py` MUST provide an async connection pool wrapper and a dependency-injection resource that yields it and closes it on shutdown. Constructing the wrapper or the resource MUST NOT open the pool or any connection; the pool MUST be opened on first use, exactly once even under concurrent first use. A failed open MUST NOT leave the adapter permanently unusable: the next use retries with a fresh pool.
- **FR-007**: Connections obtained from the wrapper MUST commit when the block succeeds and roll back when it raises, and are always returned to the pool. The wrapper meets this by delegating to the pool's own connection context, which provides these guarantees.
- **FR-008**: `psycopg_repository.py` MUST define `PsycopgRepository` with an async `ping()` that runs `SELECT 1` and returns `True`, plus a commented `find_by_id` example that opens the cursor with `row_factory=dict_row`, passes the id as a `%s` parameter, maps the row to the domain model by column name, and explains why SQL is never built with string formatting.
- **FR-009**: When `--gateway <name>` is given, the repository MUST use `@wireup.injectable(as_type=<GatewayClass>)` and inherit from `<GatewayClass>`; the wiring test `test_container_resolves_psycopg` MUST be appended and `MISSING_ADAPTERS` re-synchronized.
- **FR-010**: `test_psycopg_adapter.py` MUST run without a PostgreSQL server, using test doubles for the pool, and cover: `ping()`, that the wrapper does not open the pool at construction, that it opens it once on first use, that a failed open is retried on the next use, and that closing it closes the pool.
- **FR-011**: The generator MUST append an idempotent `psycopg_env` autouse fixture to `src/tests/conftest.py` that sets `PSYCOPG_DATABASE_URL` to a placeholder URL, reusing the shared header logic so the header is written only once.
- **FR-012**: `scaffold dm --name psycopg --confirm` MUST remove the adapter, its tests and the `psycopg_env` fixture without affecting other fixtures.
- **FR-013**: `--driver` combined with `--type psycopg` MUST exit with code 1 and state that `--driver` is only valid with `--type sqlalchemy`.
- **FR-014**: `--dry-run` MUST print the file tree and the pending dependencies without writing, and the dry-run baseline MUST include a `gda:psycopg` entry.
- **FR-015**: README MUST document `gda --type psycopg`: when to choose it over `sqlalchemy`, `PSYCOPG_DATABASE_URL`, the lazily opened pool, and parameterized queries.

### Key Entities *(include if feature involves data)*

- **PsycopgSettings**: Configuration model — `database_url` (required), `min_size` (1), `max_size` (10), `timeout` (30.0 s). Loaded from environment with the `PSYCOPG_` prefix (`PSYCOPG_DATABASE_URL`, `PSYCOPG_MIN_SIZE`, `PSYCOPG_MAX_SIZE`, `PSYCOPG_TIMEOUT`).
- **PsycopgConnectionPool**: Wrapper around the async connection pool. Created closed; opens on first use; hands out connections inside a transaction block; closed on container shutdown.
- **psycopg_pool resource**: Dependency-injection resource that yields the wrapper and closes it when the container closes.
- **PsycopgRepository**: Concrete adapter; optionally implements a domain gateway interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer generates a working psycopg adapter with one command, and all four quality checks (lint, strict typing, tests, architecture validation) pass with zero manual edits.
- **SC-002**: The generated project's full test suite passes on a machine with no database server and no container runtime.
- **SC-003**: Three adapter types (`rest-consumer`, `sqlalchemy`, `psycopg`) coexist in one project with a single, syntactically valid shared test configuration file.
- **SC-004**: Deleting the psycopg adapter leaves no orphaned fixture, import or file, and the remaining project still passes all quality checks.
- **SC-005**: No generated example builds SQL by concatenating or formatting values into the query text (0 occurrences).
- **SC-006**: Starting the generated service with an unreachable database URL does not fail at startup; the first query reports the failure within the configured timeout (30 seconds by default).

## Assumptions

- The project uses the wireup DI setup produced by `scaffold ca` (scaffold-ca-python ≥ 1.0).
- psycopg 3 is the only PostgreSQL driver for this adapter; psycopg2 and synchronous APIs are out of scope.
- `psycopg[binary]` is used because the generated Dockerfile (slim image, no build tools) cannot compile the driver from source.
- psycopg 3 and psycopg-pool ship their own type information, so strict type checking needs no stub packages.
- Default pool bounds are 1 minimum and 10 maximum connections with a 30-second timeout, overridable through environment variables; connection recycling (`max_idle`, `max_lifetime`) keeps psycopg_pool's defaults.
- The developer owns the schema and its migrations; no migration tooling is generated.
- Only one psycopg adapter per project is supported (`fixed_name = "psycopg"`); a second database requires manual configuration.
- Coexistence with the `sqlalchemy` adapter is supported at the file and dependency level; choosing which one implements a given gateway is the developer's decision.

## Clarifications

### Session 2026-11-25

- Q: Should the generated repository's commented example query return rows as dictionaries or tuples? → A: Dictionaries — a commented `find_by_id` using `cursor(row_factory=dict_row)` that maps the row to the domain model by column name (FR-008 updated).
- Q: Which connection-pool settings should `PsycopgSettings` expose? → A: `min_size` (1), `max_size` (10) and `timeout` (30.0 s), via `PSYCOPG_MIN_SIZE`, `PSYCOPG_MAX_SIZE`, `PSYCOPG_TIMEOUT` (FR-005, Key Entities, Assumptions, Edge Cases and SC-006 updated).
