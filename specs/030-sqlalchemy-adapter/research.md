# Research: SQLAlchemy Async Driven Adapter

**Feature**: 030-sqlalchemy-adapter | **Date**: 2026-11-23

## Decision 1: PostgreSQL driver — psycopg vs asyncpg

**Decision**: Use `psycopg[binary]` (psycopg 3).

**Rationale**:
- psycopg 3 has first-class support for SQLAlchemy's async interface via the `postgresql+psycopg://` dialect.
- `asyncpg` requires the `asyncpg` dialect (`postgresql+asyncpg://`) and has a different connection pool lifecycle.
- psycopg 3 was validated in the reference `ms_library` project with `psycopg[binary]~=3.2.x`.
- `psycopg[binary]` bundles the C extension, avoiding the extra step of building from source on deployment.

**Alternatives considered**:
- `asyncpg`: Faster raw throughput but stricter typing and no prepared-statement caching by default in async mode. Incompatible URL scheme would require a different settings example.
- `psycopg2` / `psycopg2-binary`: Synchronous only; incompatible with SQLAlchemy async.

## Decision 2: In-memory SQLite engine — `StaticPool`

**Decision**: Use `create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)` in generated tests.

**Rationale**:
- The default `NullPool` discards the connection after each `async with engine.begin()` block. For an in-memory SQLite database this means the schema (created by `Base.metadata.create_all`) is lost on the next connection.
- `StaticPool` reuses the same underlying connection for all requests, keeping the in-memory schema alive for the duration of a test session.
- `check_same_thread=False` is required by SQLite to allow the connection to be used from the async event loop.

**Alternatives considered**:
- File-based SQLite (`:memory:` → `test.db`): Requires cleanup between tests; avoided.
- `NullPool` with `Base.metadata.create_all` per test: Verbose and slower.

## Decision 3: `expire_on_commit=False` in async_sessionmaker

**Decision**: Generate `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`.

**Rationale**:
- After a commit, SQLAlchemy marks all ORM objects as expired by default. In async contexts, accessing an expired attribute triggers lazy loading, which raises `sqlalchemy.exc.MissingGreenlet` because there is no coroutine to yield from.
- Setting `expire_on_commit=False` disables automatic expiry, so attributes remain accessible after commit without triggering an extra database round-trip.
- This is the documented best practice for async SQLAlchemy (see SQLAlchemy async docs).

**Alternatives considered**:
- Leave default (`expire_on_commit=True`) and let the developer fix it: Poor DX — the error is confusing and not obvious from the generated code.
- Use `expire_on_commit=True` with explicit `refresh()` calls in example methods: More verbose and still non-obvious.

## Decision 4: Why no Alembic

**Decision**: Alembic is out of scope for the scaffold.

**Rationale**:
- Alembic requires a migration history directory, `env.py`, and `alembic.ini`. Adding these to the scaffold output would make the generated project opinionated about migration tooling.
- Teams may prefer alternatives (Flyway via Docker, manual DDL, raw `create_all` for development-only schemas).
- The `sqlalchemy_models.py` template includes a comment directing the developer to set up Alembic or their preferred migration tool.

## Decision 5: `psycopg[binary]` version pin

**Decision**: Pin as `psycopg[binary]~=3.2.0` (three-part `~=` per project convention).

**Rationale**: The project convention (see `dependency-pinning-preference.md` in memory) uses `~=` with three-part version specifiers for factory-injected deps. `3.2.0` was available at spec creation time; verify latest 3.2.x on PyPI at implementation time and update if a newer patch is available.

**At implementation time**: run `uv pip index versions psycopg` and use the latest `3.2.x` release.

## Decision 6: ORM models location

**Decision**: `sqlalchemy_models.py` lives in `infrastructure/driven_adapters/sqlalchemy/`.

**Rationale**: ORM mapper classes are infrastructure-layer code (they depend on SQLAlchemy, an external library). They are distinct from domain entities in `domain/model/`. Clean Architecture Principle I is maintained: domain layer does not import from infrastructure.
