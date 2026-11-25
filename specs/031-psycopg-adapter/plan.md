# Implementation Plan: psycopg Async Driven Adapter

**Branch**: `feature/031-psycopg-adapter` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-psycopg-adapter/spec.md`

## Summary

Add `--type psycopg` to `scaffold gda` to generate an async PostgreSQL adapter that runs plain SQL through psycopg 3 and `psycopg_pool.AsyncConnectionPool`, with no ORM. The pool is wrapped in a `PsycopgConnectionPool` that opens lazily — once, under an `asyncio.Lock`, building a fresh pool on each attempt so a failed open can be retried — which keeps container creation and the wiring test free of database connections. The factory reuses the 030 extension points (`append_env_fixture`, `append_wiring_test`, the generic `dm` fixture cleanup) and adds no new base-class API.

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**: psycopg 3.3 (`psycopg[binary]`), psycopg-pool 3.3, wireup 2.13, pydantic-settings 2.x

**Storage**: Generated adapter connects to PostgreSQL through `PSYCOPG_DATABASE_URL`

**Testing**: pytest + pytest-cov in the CLI; generated project tests use `unittest.mock` doubles for the pool (no server, no Docker)

**Target Platform**: Linux/macOS/CI, and the generated `python:3.13-slim` Docker image (binary wheels, no compiler)

**Project Type**: CLI code-generation tool; generated output is an async Python microservice

**Performance Goals**: N/A for the scaffold; first query in the generated service fails within `PSYCOPG_TIMEOUT` (default 30 s) when the database is unreachable

**Constraints**: Generated code passes ruff, mypy --strict, pytest and `scaffold vs` with zero edits; container creation opens no connection; `--driver` stays sqlalchemy-only

**Scale/Scope**: One psycopg adapter per project (`fixed_name = "psycopg"`); ~5 templates, 1 factory, 2 dependency constants (1 new), registry and `dm` map entries, docs

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Clean Architecture | ✅ Pass | All generated code lives in `infrastructure/driven_adapters/psycopg/`; the gateway import goes inward (infrastructure → domain); the commented example maps rows to the domain model inside the adapter |
| II. Template-Driven Code Generation | ✅ Pass | Every generated file comes from `templates/driven_adapter/psycopg/*.jinja2`; rendering tests added to `tests/templates/test_driven_adapter_templates.py` (one block per template group, as for sqlalchemy) |
| III. Full Command Parity | ✅ Pass (PATCH) | `gda` gains the `psycopg` type; the Principle III table is updated in the same branch (documentation-only PATCH, as done for `sqlalchemy`) |
| IV. Python-First Idioms | ✅ Pass | Native async psycopg 3 API; psycopg and psycopg-pool ship `py.typed`, so mypy --strict needs no stubs (verified in research R-3) |
| V. Test-First Development | ✅ Pass | tasks.md orders failing tests before implementation; the generated project ships `test_psycopg_adapter.py` |
| VI. Developer Experience | ✅ Pass | `--dry-run` tree and pending deps, `--help` example, existing `--driver` misuse error with hint |
| VII. Git Workflow | ✅ Pass | Branch `feature/031-psycopg-adapter` |
| VIII. Clean Code & Fast Tests | ✅ Pass | No new function exceeds 5 positional args or complexity 10; `@override` on `build_extra`; no SQL built with string formatting in templates; no real `uv` call outside `tests/e2e/` |

**Constitution Check Result: PASS**

*Post-design re-check (after Phase 1)*: PASS — the design adds no base-class API, no new CLI flag and no layer crossing.

## Project Structure

### Documentation (this feature)

```text
specs/031-psycopg-adapter/
├── plan.md              # This file
├── research.md          # Phase 0: pool lifecycle, reopen behavior, typing, deps
├── data-model.md        # Phase 1: generated entities
├── contracts/
│   └── generated-files.md  # Phase 1: file tree, deps, conftest and CLI contract
├── quickstart.md        # Phase 1: validation scenarios
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code

```text
src/scaffold_ca_python/
├── commands/generate_driven_adapter.py       # --type help text + epilog example
├── factory/
│   ├── dependencies.py                       # add PSYCOPG_POOL (reuse PSYCOPG_BINARY)
│   ├── driven_adapters/
│   │   ├── __init__.py                       # register "psycopg"
│   │   └── da_psycopg.py                     # NEW factory
│   └── simple/delete_module_factory.py       # add psycopg → psycopg_env
└── templates/driven_adapter/psycopg/         # NEW
    ├── __init__.py.jinja2
    ├── psycopg_settings.py.jinja2
    ├── psycopg_config.py.jinja2
    ├── psycopg_repository.py.jinja2
    └── test_psycopg_adapter.py.jinja2

tests/
├── factory/driven_adapters/test_da_psycopg.py     # NEW
├── factory/test_registry.py                       # registry set + fixed_name
├── factory/test_dry_run_parity.py                 # gda:psycopg parametrization
├── factory/fixtures/dry_run_baseline.json         # gda:psycopg entry
├── templates/test_driven_adapter_templates.py     # psycopg rendering tests
├── commands/test_generate_driven_adapter.py       # dry-run output, idempotency, --driver misuse
├── commands/test_behavior_contract.py             # unknown-type list, 3-adapter coexistence, dm
└── e2e/test_generated_project_quality.py          # scenarios 14 and 15

README.md                                          # psycopg section + tables
.specify/memory/constitution.md                    # Principle III table (PATCH)
```

**Structure Decision**: Single project. The new factory mirrors `da_sqlalchemy.py`; everything else is a registry or list entry.

## Complexity Tracking

> No constitution violations requiring justification.

## Design Decisions

### DD-1: Lazy, retryable pool wrapper

`PsycopgConnectionPool` holds the settings, an `asyncio.Lock` and `_pool: AsyncConnectionPool | None = None`. `connection()` (an `@asynccontextmanager`) calls `_ensure_open()`, which, under the lock and only while `_pool is None`, builds a new `AsyncConnectionPool(conninfo, min_size, max_size, timeout, open=False)` and awaits `open(wait=True, timeout=settings.timeout)`; the pool is stored only after a successful open. It then delegates to `async with self._pool.connection() as conn`, which commits on success and rolls back on error. `close()` closes the stored pool if any.

**Rationale**: The wiring test resolves the whole chain against a placeholder URL, so nothing may connect at construction (R-1). A pool whose open failed can never be reopened (`PoolClosed`, R-2), so reusing one instance would turn a transient outage at first use into a permanent failure.

### DD-2: Resource yields the wrapper

`@wireup.injectable async def psycopg_pool(settings: PsycopgSettings) -> AsyncIterator[PsycopgConnectionPool]` yields a wrapper and calls `await pool.close()` in `finally`, mirroring `sqlalchemy_engine` in `templates/driven_adapter/sqlalchemy/sqlalchemy_config.py.jinja2`.

**Rationale**: Same lifecycle contract as the sqlalchemy engine; the container closes the pool on shutdown even when it was never opened (closing a never-opened pool is a no-op, R-1).

### DD-3: Separate `psycopg-pool` requirement

`runtime_dependencies = (PSYCOPG_BINARY, PSYCOPG_POOL, PYDANTIC_SETTINGS)` with the new constant `PSYCOPG_POOL = "psycopg-pool~=3.3.3"`. The `psycopg[binary,pool]` extra is not used.

**Rationale**: `core/pyproject_writer.py` deduplicates by bare package name, ignoring extras. If the sqlalchemy adapter already declared `psycopg[binary]`, a later `psycopg[binary,pool]` would be skipped and the pool would never be installed (R-4).

### DD-4: No changes to the base class or CLI flags

`DrivenAdapterPsycopg.build_extra` only calls `self.append_env_fixture(builder, conftest_path, "psycopg_env", _CONFTEST_FIXTURE)`. No dev-group or driver logic is needed: psycopg 3 is typed (R-3) and `_apply_driver_param` in `commands/generate_driven_adapter.py` already rejects `--driver` for every type except sqlalchemy.

**Rationale**: Smallest change that satisfies the spec; the 030 extension points were designed for this.

### DD-5: Dictionary rows in the example query

The commented `find_by_id` opens `conn.cursor(row_factory=dict_row)`, passes the id as a `%s` parameter, and maps the row to the domain model by column name (clarification 2026-11-25). A short *why* comment states that values are never formatted into SQL.

**Rationale**: Name-based mapping survives column reordering and matches the Pydantic domain models generated by `scaffold gm`.
