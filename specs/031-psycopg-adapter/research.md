# Research: psycopg Async Driven Adapter

All findings were verified on 2026-11-25 in an isolated environment (`uv run --no-project --with "psycopg[binary]~=3.3.9" --with "psycopg-pool~=3.3.3"`) against an unreachable address (`127.0.0.1:1`).

## R-1: When does `AsyncConnectionPool` connect?

**Decision**: Construct the pool with `open=False` and open it on first use, not in the DI resource.

**Findings**:
- `AsyncConnectionPool(conninfo, ..., open=False)` performs no I/O; `pool.closed` is `True` after construction.
- `await pool.close()` on a never-opened pool returns without error.
- `templates/driven_adapter/wiring_test_stub.py.jinja2` resolves the gateway with `await container.get(<Gateway>)`, which runs every resource in the chain up to its `yield`. An `open()` inside the resource would start background connection attempts against the placeholder URL set by the `psycopg_env` conftest fixture, logging connection errors during the test run.

**Alternatives considered**:
- `open()` in the resource with `wait=False`: connects in the background at container creation; noisy and couples startup to database availability (contradicts SC-006).
- `min_size=0`: still starts pool workers on `open()`; does not remove the startup coupling.

## R-2: Can a pool be reopened after a failed open?

**Decision**: Build a fresh `AsyncConnectionPool` on every open attempt; store it only after a successful open.

**Findings**:
- `await pool.open(wait=True, timeout=1.0)` against an unreachable server raises `psycopg_pool.PoolTimeout` after the timeout ("pool initialization incomplete after 1.0 sec") and leaves the pool closed.
- A second `open()` on the same instance raises `psycopg_pool.PoolClosed` ("pool has already been opened/closed and cannot be reused").

**Implication**: a wrapper that keeps one pool instance would stay broken after a single failed first query until the process restarts. Creating the pool inside the locked open path makes recovery automatic once the database is back.

## R-3: Typing under `mypy --strict`

**Decision**: No stub packages; annotate the pool as `AsyncConnectionPool[AsyncConnection[tuple[Any, ...]]]`.

**Findings**: psycopg and psycopg-pool ship `py.typed`. A probe module with that annotation, an `@asynccontextmanager` yielding `AsyncConnection[tuple[Any, ...]]`, and a `conn.cursor(row_factory=dict_row)` query returning `dict[str, Any] | None` passes `mypy --strict` with no errors.

## R-4: How to declare the pool dependency

**Decision**: Add `PSYCOPG_POOL = "psycopg-pool~=3.3.3"` as a separate requirement and reuse `PSYCOPG_BINARY = "psycopg[binary]~=3.3.9"`.

**Findings**:
- PyPI latest: psycopg 3.3.9, psycopg-pool 3.3.3 (both `requires_python >= 3.10`).
- `core/pyproject_writer.py` (`inject_dependencies`, `inject_group_dependencies`) skips a requirement whose bare name — extras stripped — already exists. With the sqlalchemy adapter generated first, `psycopg[binary,pool]` would be skipped as a duplicate of `psycopg[binary]`, leaving `psycopg_pool` uninstalled.

**Alternatives considered**: the `psycopg[binary,pool]` extra (rejected for the reason above); pinning psycopg-pool with `==` (rejected: factories use `~=` per the project pinning convention).

## R-5: Binary vs source build

**Decision**: `psycopg[binary]`.

**Findings**: the generated Dockerfile (`templates/project/dockerfile.jinja2`) uses `python:3.13-slim` and installs no system packages; building psycopg from source needs `libpq-dev` and a compiler. The binary wheel bundles libpq.

## R-6: Generated tests without a database

**Decision**: `unittest.mock` doubles. The repository test receives a fake wrapper whose `connection()` yields a mock connection/cursor; the wrapper tests patch `AsyncConnectionPool` in the generated `psycopg_config` module.

**Rationale**: generated projects must pass `pytest` with no server and no container runtime (SC-002). The wrapper's lifecycle — lazy open, single open under concurrency, retry after a failed open, close — is exactly what a real server would not exercise deterministically anyway.
