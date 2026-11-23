# Implementation Plan: SQLAlchemy Async Driven Adapter

**Branch**: `feature/030-sqlalchemy-adapter` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/030-sqlalchemy-adapter/spec.md`

## Summary

Add `--type sqlalchemy` to `scaffold gda` to generate a production-ready async SQLAlchemy 2 adapter. The generated adapter uses wireup DI, an async engine resource, `async_sessionmaker` with `expire_on_commit=False`, a `Base(DeclarativeBase)` for ORM models, and driver selection via `--driver postgresql|sqlite` (default: postgresql / `psycopg[binary]`). Two bugs from the prototype are fixed: shared `conftest.py` header written only once across adapter types; `dm` generalized to remove any `<module>_env` fixture.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: SQLAlchemy 2.x (asyncio extra), wireup 2.13, pydantic-settings 2.x, psycopg[binary] (postgresql driver), aiosqlite (sqlite / test driver)

**Storage**: Generated adapter connects to PostgreSQL (default) or SQLite (via `--driver sqlite`)

**Testing**: pytest + pytest-cov; generated project tests run against in-memory SQLite with `StaticPool`

**Target Platform**: Any platform where the scaffold CLI and the generated project run (Linux/macOS/CI)

**Project Type**: CLI code-generation tool (scaffold-ca-python); generated output is an async Python microservice

**Performance Goals**: N/A for the scaffold itself; generated adapter `ping()` must resolve within normal I/O timeout

**Constraints**: Generated code must pass ruff, mypy --strict, pytest, and `scaffold vs` with zero manual edits; `--driver` is exclusive to `--type sqlalchemy`

**Scale/Scope**: Single SQLAlchemy adapter per project (`fixed_name = "sqlalchemy"`); feature adds ~6 templates, 1 factory, 1 command flag, and updates `dm`

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clean Architecture | ✅ Pass | Generated adapter lives in `infrastructure/driven_adapters/sqlalchemy/`; `sqlalchemy_models.py` defines `Base` there (ORM mapping belongs to infrastructure); domain layer untouched |
| II. Template-Driven Code Generation | ✅ Pass | All 5 source files and 1 test file come from Jinja2 templates under `templates/driven_adapter/sqlalchemy/`; `tests/templates/` test must be added for this new group (FR-requirement, not pre-existing debt) |
| III. Full Command Parity | ⚠️ Amendment | Constitution Principle III lists `gda` types as `rest-consumer`, `secrets`, `generic`. Adding `sqlalchemy` extends the list; this is an intentional expansion. The constitution's governance allows new features to extend capability; no amendment doc required beyond noting it here |
| IV. Python-First Idioms | ✅ Pass | Type hints, mypy strict, ruff, uv, async/await in generated code |
| V. Test-First Development | ✅ Pass | Tests written before implementation (tasks.md enforces red-green-refactor order); generated project includes `test_sqlalchemy_adapter.py` |
| VI. Developer Experience | ✅ Pass | Rich output, `--dry-run`, `--help` with example, driver error hints |
| VII. Git Workflow | ✅ Pass | Branch `feature/030-sqlalchemy-adapter` follows `feature/<name>` convention |

**Constitution Check Result: PASS** (Principle III note is informational, not a violation)

## Project Structure

### Documentation (this feature)

```text
specs/030-sqlalchemy-adapter/
├── plan.md              # This file
├── research.md          # Phase 0: driver choice, StaticPool, expire_on_commit
├── data-model.md        # Phase 1: entities and relationships
├── contracts/
│   └── generated-files.md  # Phase 1: file tree, deps, conftest contract
├── quickstart.md        # Phase 1: manual validation steps
└── tasks.md             # Phase 2 (speckit-tasks output)
```

### Source Code

```text
src/scaffold_ca_python/
├── factory/
│   ├── dependencies.py                           # add PSYCOPG_BINARY constant
│   ├── driven_adapters/
│   │   ├── __init__.py                           # already has sqlalchemy entry
│   │   ├── base.py                               # add append_env_fixture() helper
│   │   └── da_sqlalchemy.py                      # update: driver param, models file, deps
│   └── simple/
│       └── delete_module_factory.py              # generalize conftest fixture removal
├── templates/driven_adapter/sqlalchemy/
│   ├── __init__.py.jinja2                        # (exists, no change)
│   ├── sqlalchemy_config.py.jinja2               # update: sessionmaker + expire_on_commit=False
│   ├── sqlalchemy_models.py.jinja2               # NEW: Base(DeclarativeBase) + example
│   ├── sqlalchemy_repository.py.jinja2           # update: use sessionmaker, session-based ping()
│   ├── sqlalchemy_settings.py.jinja2             # (exists, minor: URL example for driver)
│   └── test_sqlalchemy_adapter.py.jinja2         # update: StaticPool + create_all + ping()
└── commands/
    └── generate_driven_adapter.py                # add --driver DbDriver option

tests/
├── factory/
│   └── driven_adapters/
│       └── test_da_sqlalchemy.py                 # update: driver param tests
├── templates/
│   └── test_sqlalchemy_templates.py              # NEW (Constitution Principle II)
├── commands/
│   ├── test_generate_driven_adapter.py           # update: driver flag tests
│   └── test_behavior_contract.py                 # update: --driver validation
├── e2e/
│   └── test_generated_project_quality.py         # add scenarios 11 + 12
└── factory/
    └── fixtures/
        └── dry_run_baseline.json                 # already updated (port)
```

**Structure Decision**: Single project structure. All new code is under the existing `src/scaffold_ca_python/` tree, following the same pattern as `da_rest_consumer.py`.

## Complexity Tracking

> No constitution violations requiring justification.

## Design Decisions

### DD-1: Driver-conditional runtime dependency

`runtime_dependencies` ClassVar stays with only `SQLALCHEMY` and `PYDANTIC_SETTINGS` (driver-agnostic). `build_extra` reads `builder.get_param("driver")` and calls `builder.add_dependency(PSYCOPG_BINARY)` or `builder.add_dependency(AIOSQLITE)`. `AIOSQLITE` always goes in the `test` group regardless of driver.

**Rationale**: ClassVars are static; driver choice is dynamic. Following the existing `build_extra` extension point avoids adding new API surface to `DrivenAdapterFactory`.

### DD-2: Shared conftest.py header written only once

`DrivenAdapterFactory.base` gains a new static method `append_env_fixture(builder, conftest_path, fixture_name, fixture_body)`. It reads the existing file (if any); if `import pytest` is already present it omits the header block and appends only the fixture body. Both `da_rest_consumer` and `da_sqlalchemy` are refactored to call this helper, removing their local `_CONFTEST_HEADER` duplicates.

**Rationale**: The current `append_to_file(marker=...)` only prevents duplicate fixture functions; it does not prevent a second header when two separate adapters both prepend the header.

### DD-3: Generalized `dm` conftest cleanup

`DeleteModuleFactory._remove_rest_consumer_conftest_fixture` is replaced by a generic `_remove_conftest_fixture(tests_root, fixture_name)`. The `build` method calls it whenever the deleted module is any driven adapter with a known `fixed_name` that has an env fixture (`rest_consumer`, `sqlalchemy`). The regex pattern is parameterized on `fixture_name`.

**Rationale**: The existing approach requires touching `delete_module_factory.py` for every new adapter type with a conftest fixture. The generic version needs no further changes.

### DD-4: `--driver` as `Optional[DbDriver]` in Typer

`DbDriver` is an `StrEnum` with values `postgresql` and `sqlite`. The Typer option has `default=None`. Validation logic: if `type_` is not `sqlalchemy` and `driver` is not `None` → `fail()` with exit code 1. If `type_` is `sqlalchemy` and `driver` is `None` → resolve to `postgresql` and log "Driver: postgresql (default)". An unknown string value triggers Typer's built-in exit code 2.

**Rationale**: `None` as default distinguishes "not specified" from "specified explicitly", so the validation can detect misuse with other adapter types without false positives.

### DD-5: `sqlalchemy_models.py` location

The models file lives inside `infrastructure/driven_adapters/sqlalchemy/` alongside the other adapter files. It is intentionally not placed in `domain/model/` because it contains SQLAlchemy-specific ORM mapping code (infrastructure concern). Real domain models remain in `domain/model/`; the ORM entities in `sqlalchemy_models.py` are infrastructure-layer mapping classes.

**Rationale**: Aligns with Clean Architecture Principle I — ORM classes are infrastructure adapters, not domain entities.
