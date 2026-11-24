# Feature Specification: SQLAlchemy Async Driven Adapter

**Feature Branch**: `feature/030-sqlalchemy-adapter`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "scaffold gda --type sqlalchemy generates a complete async SQLAlchemy 2 driven adapter with driver selection, gateway support, and coexistence with other adapter types"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generate SQLAlchemy Adapter (Priority: P1)

A developer scaffolds a new SQLAlchemy async adapter with a single command. The generated files are immediately compilable and all quality checks pass without manual intervention. The developer can choose between PostgreSQL (default) or SQLite drivers.

**Why this priority**: Core value proposition — the adapter must be usable out of the box. Without this, the feature delivers no value.

**Independent Test**: Run `scaffold gda --type sqlalchemy` in a new scaffold project, then run ruff, mypy --strict, pytest, and `scaffold vs`. All must pass with zero manual edits.

**Acceptance Scenarios**:

1. **Given** a scaffold project exists, **When** `scaffold gda --type sqlalchemy` is run, **Then** five source files are created (`__init__.py`, `sqlalchemy_settings.py`, `sqlalchemy_config.py`, `sqlalchemy_models.py`, `sqlalchemy_repository.py`) plus one test file (`test_sqlalchemy_adapter.py`), and `psycopg[binary]` is added to runtime dependencies.
2. **Given** the adapter is generated without `--driver`, **When** the CLI output is inspected, **Then** it shows "Driver: postgresql (default)".
3. **Given** `--driver sqlite` is specified, **When** the adapter is generated, **Then** `aiosqlite` is the runtime dependency (not `psycopg[binary]`), and URL examples use `sqlite+aiosqlite:///:memory:`.
4. **Given** `--driver postgresql` is specified on a non-sqlalchemy type (e.g., `--type rest-consumer`), **When** the command runs, **Then** it exits with code 1 and an explanatory error message.
5. **Given** `SQLALCHEMY_DATABASE_URL` is set in the environment, **When** the generated project tests run, **Then** they pass against the configured database.
6. **Given** the project already has the sqlalchemy adapter, **When** `scaffold gda --type sqlalchemy` is run again, **Then** the env fixture in `conftest.py` is not duplicated (idempotent).

---

### User Story 2 - Gateway Integration (Priority: P1)

A developer binds the SQLAlchemy adapter to a domain gateway interface, enabling dependency injection to wire it automatically. The wiring test and `MISSING_ADAPTERS` are updated to reflect the binding.

**Why this priority**: Gateway binding is required for real-world DI-based projects. Without it the adapter is not wired into the application.

**Independent Test**: Run `scaffold gda --type sqlalchemy --gateway book_repository` and verify that the repository class inherits from `BookRepository`, the wiring test file contains a test for it, and `MISSING_ADAPTERS` no longer lists `book_repository`.

**Acceptance Scenarios**:

1. **Given** a scaffold project with a `book_repository` gateway, **When** `scaffold gda --type sqlalchemy --gateway book_repository` is run, **Then** the repository class uses `as_type=BookRepository` in the wireup decorator and inherits from `BookRepository`.
2. **Given** the adapter is generated with `--gateway`, **When** the wiring test file is inspected, **Then** it contains `test_container_resolves_sqlalchemy`.
3. **Given** `MISSING_ADAPTERS` listed `book_repository` before generation, **When** the adapter is generated with `--gateway book_repository`, **Then** `book_repository` is removed from `MISSING_ADAPTERS`.

---

### User Story 3 - Coexistence and Cleanup (Priority: P2)

A developer adds both a `rest-consumer` and a `sqlalchemy` adapter to the same project. Both share a single valid `conftest.py`. When the SQLAlchemy adapter is deleted with `scaffold dm`, its fixture is removed without breaking the rest-consumer fixture.

**Why this priority**: Practical multi-adapter projects are common; a broken `conftest.py` would fail all tests. Cleanup is secondary but required for a complete lifecycle.

**Independent Test**: Generate both adapters, verify `conftest.py` parses cleanly (`ast.parse`), then delete the sqlalchemy adapter and verify `conftest.py` still contains `rest_consumer_env` but not `sqlalchemy_env`.

**Acceptance Scenarios**:

1. **Given** a project with no adapters, **When** `rest-consumer` and then `sqlalchemy` are generated in sequence, **Then** `conftest.py` is syntactically valid Python and contains both `rest_consumer_env` and `sqlalchemy_env` fixtures.
2. **Given** a project with both adapters, **When** `scaffold dm --name sqlalchemy --confirm` is run, **Then** `sqlalchemy_env` is removed from `conftest.py` and `rest_consumer_env` remains.
3. **Given** only the sqlalchemy adapter is present, **When** `scaffold dm --name sqlalchemy --confirm` is run, **Then** the sqlalchemy-related fixture is removed cleanly.

---

### Edge Cases

- What happens when `--driver` receives an unrecognized value (e.g., `--driver oracle`)? → Exit code 2 with a clear error listing allowed values.
- What happens if `conftest.py` already contains `sqlalchemy_env` when the adapter is regenerated? → The fixture is not appended again (idempotent marker check).
- What happens if the project has no `src/tests/conftest.py`? → The file is created with the full header and fixture.
- What happens if `psycopg[binary]` is already in dependencies when regenerating? → The injector skips the duplicate (existing behavior of `inject_dependencies`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The CLI MUST accept `--driver {postgresql,sqlite}` exclusively on `--type sqlalchemy`; using `--driver` with any other type MUST exit with code 1 and explain the restriction.
- **FR-002**: When `--driver` is omitted with `--type sqlalchemy`, the system MUST default to `postgresql`, add `psycopg[binary]` as a runtime dependency, and display "Driver: postgresql (default)" in CLI output.
- **FR-003**: When `--driver sqlite` is specified, the system MUST add `aiosqlite` as a runtime dependency instead of `psycopg[binary]`.
- **FR-004**: `aiosqlite` MUST always be added to the `test` dependency group regardless of driver, to support in-memory SQLite testing.
- **FR-005**: The generator MUST create five source files: `__init__.py`, `sqlalchemy_settings.py`, `sqlalchemy_config.py`, `sqlalchemy_models.py`, `sqlalchemy_repository.py` under `infrastructure/driven_adapters/sqlalchemy/`.
- **FR-006**: The generator MUST create one test file: `test_sqlalchemy_adapter.py` under `src/tests/infrastructure/driven_adapters/sqlalchemy/`.
- **FR-007**: `sqlalchemy_settings.py` MUST define `SQLAlchemySettings` with a required `database_url` field, `echo: bool = False`, and `env_prefix="SQLALCHEMY_"`.
- **FR-008**: `sqlalchemy_config.py` MUST define an async engine resource and an `async_sessionmaker[AsyncSession]` injectable configured with `expire_on_commit=False` to prevent `MissingGreenlet` errors in async contexts.
- **FR-009**: `sqlalchemy_models.py` MUST define `class Base(DeclarativeBase)` and include a commented example model.
- **FR-010**: `sqlalchemy_repository.py` MUST use `async_sessionmaker` for session management and include a `ping()` method plus a commented example method.
- **FR-011**: `test_sqlalchemy_adapter.py` MUST use a real in-memory SQLite engine (`sqlite+aiosqlite:///:memory:` with `StaticPool`), call `Base.metadata.create_all` via `run_sync` to demonstrate ORM table creation, assert `ping()` returns `True`, and not use mocks for the engine.
- **FR-012**: The generator MUST append an idempotent `sqlalchemy_env` fixture to `src/tests/conftest.py` that sets `SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///:memory:`.
- **FR-013**: When `--gateway <name>` is specified, the repository MUST use `@wireup.injectable(as_type=<GatewayClass>)` and inherit from `<GatewayClass>`.
- **FR-014**: The `conftest.py` header (docstring, `from __future__`, `import pytest`) MUST be written only once even when multiple adapter types append fixtures.
- **FR-015**: `scaffold dm --name sqlalchemy` MUST remove the `sqlalchemy_env` fixture block from `conftest.py` without affecting other fixtures.
- **FR-016**: An unrecognized `--driver` value MUST exit with code 2 and list allowed values.
- **FR-017**: The dry-run baseline JSON MUST include the `gda:sqlalchemy` entry with the correct file list.
- **FR-018**: README MUST document `gda --type sqlalchemy`, `--driver`, `SQLALCHEMY_DATABASE_URL`, and instructions for adding models and migrations manually.

### Key Entities *(include if feature involves data)*

- **SQLAlchemySettings**: Configuration model — `database_url` (required), `echo` (bool, default False). Loaded from environment with `SQLALCHEMY_` prefix.
- **AsyncEngine**: Async database connection pool, managed as a wireup resource (created on startup, disposed on shutdown).
- **async_sessionmaker**: Session factory injected into the repository; produces `AsyncSession` instances per operation.
- **Base (DeclarativeBase)**: SQLAlchemy ORM base class; user extends it to define domain models.
- **SQLAlchemyRepository**: Concrete adapter class; optionally implements a domain gateway interface.
- **DbDriver**: Enum with values `postgresql` and `sqlite`; controls runtime dependency selection.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can generate a working SQLAlchemy adapter with a single command and have all quality checks pass with zero manual edits.
- **SC-002**: The generated project's tests pass against an in-memory SQLite database without any additional configuration.
- **SC-003**: Two adapter types (`rest-consumer` + `sqlalchemy`) can coexist in the same project without syntax errors in the shared test configuration file.
- **SC-004**: The `scaffold dm` command removes the SQLAlchemy adapter cleanly, leaving no orphaned fixtures or broken imports in the test configuration file.
- **SC-005**: Generating the adapter twice does not produce duplicate entries in any configuration file or test fixture.
- **SC-006**: An invalid driver value produces an informative error message within one second, with no partial file writes.

## Assumptions

- The project already has the wireup DI framework set up (generated via `scaffold gep --type restapi` or equivalent).
- The developer is responsible for defining domain models by extending `Base`; the scaffold only provides the base class and an example.
- Database migrations (Alembic or similar) are out of scope; the developer manages schema evolution independently.
- Only one SQLAlchemy adapter per project is supported (`fixed_name = "sqlalchemy"`); multiple databases require manual configuration.
- The in-memory SQLite engine used in tests is for unit/integration testing only; production uses PostgreSQL via psycopg.
- psycopg 3 (`psycopg[binary]`) is the default PostgreSQL driver because it supports the SQLAlchemy async interface natively and was validated in the reference ms_library project.

## Clarifications

### Session 2026-11-23

- Q: Should the generated `async_sessionmaker` be configured with `expire_on_commit=False`? → A: Yes — generate `async_sessionmaker(..., expire_on_commit=False)` with an explanatory comment (FR-008 updated).
- Q: Should `test_sqlalchemy_adapter.py` include a `Base.metadata.create_all` call to demonstrate ORM table creation, in addition to testing `ping()`? → A: Yes — test calls `Base.metadata.create_all(sync_engine)` via `run_sync`, then asserts `ping()` returns `True` (FR-011 updated).
