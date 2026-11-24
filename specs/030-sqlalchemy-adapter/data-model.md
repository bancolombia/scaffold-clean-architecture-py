# Data Model: SQLAlchemy Async Driven Adapter

**Feature**: 030-sqlalchemy-adapter | **Date**: 2026-11-23

## Entities

### DbDriver (Enum)

Enum controlling which database driver is added as a runtime dependency.

| Field | Type | Description |
|-------|------|-------------|
| `postgresql` | StrEnum value | Default; adds `psycopg[binary]` to runtime deps |
| `sqlite` | StrEnum value | Adds `aiosqlite` to runtime deps |

**Validation**: Typer enforces `--driver` accepts only these values (exit code 2 for unknown). Used only with `--type sqlalchemy` (exit code 1 otherwise).

---

### SQLAlchemySettings (generated)

Pydantic-settings model loaded from environment. Injected as a wireup singleton.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `database_url` | `str` | Yes | — | Full async SQLAlchemy URL (e.g. `postgresql+psycopg://user:pass@host/db`) |
| `echo` | `bool` | No | `False` | Log all SQL statements if `True`; set to `True` only for debugging |

**Env prefix**: `SQLALCHEMY_` (from `model_config = SettingsConfigDict(env_prefix="SQLALCHEMY_", extra="ignore")`).

**Test default**: `SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:///:memory:` (set by `sqlalchemy_env` fixture).

---

### AsyncEngine (generated)

Wireup async resource (generator-style). One engine per application lifetime.

| Aspect | Value |
|--------|-------|
| Created by | `create_async_engine(settings.database_url, echo=settings.echo)` |
| Lifecycle | Resource — started on app startup, `await engine.dispose()` in `finally` |
| Wire-up type | `AsyncIterator[AsyncEngine]` injectable |

---

### async_sessionmaker (generated)

Wireup injectable. Configured once and injected into the repository.

| Aspect | Value |
|--------|-------|
| Type | `async_sessionmaker[AsyncSession]` |
| Config | `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)` |
| `expire_on_commit` | `False` — prevents `MissingGreenlet` on attribute access after commit |

---

### Base (generated, in `sqlalchemy_models.py`)

SQLAlchemy declarative base. Developers extend it to define ORM entities.

| Aspect | Value |
|--------|-------|
| Class | `class Base(DeclarativeBase)` |
| Module | `infrastructure/driven_adapters/sqlalchemy/sqlalchemy_models.py` |
| Usage | `class BookORM(Base): __tablename__ = "books"; ...` |

---

### SQLAlchemyRepository (generated)

Concrete outbound adapter. Receives `async_sessionmaker` via constructor injection.

| Field | Type | Description |
|-------|------|-------------|
| `_sessions` | `async_sessionmaker[AsyncSession]` | Session factory (injected) |

**Key methods**:
- `ping() -> bool` — executes `SELECT 1` to confirm connectivity; returns `True` on success.
- Example commented method demonstrating `async with self._sessions() as session: ...`.

**Gateway binding (optional)**: When `--gateway <name>` is specified:
- Decorator: `@wireup.injectable(as_type=<GatewayClass>)`.
- Class declaration: `class SQLAlchemyRepository(<GatewayClass>)`.

---

## Relationships

```
DbDriver ──► da_sqlalchemy.build_extra() ──► runtime dependency injected
                                           └► PSYCOPG_BINARY (postgresql)
                                           └► AIOSQLITE (sqlite)

SQLAlchemySettings ──► AsyncEngine ──► async_sessionmaker ──► SQLAlchemyRepository
```

## Configuration File Changes

| File | Change |
|------|--------|
| `pyproject.toml` (generated project) | Adds `sqlalchemy[asyncio]~=2.1.8`, `pydantic-settings~=2.15.0`, driver dep to `[project.dependencies]`; adds `aiosqlite~=0.22.1` to `[dependency-groups.test]` |
| `src/tests/conftest.py` (generated project) | Idempotent append of `sqlalchemy_env` fixture setting `SQLALCHEMY_DATABASE_URL` |
| `src/<pkg>/application/config/wiring.py` (generated project, `--gateway`) | `MISSING_ADAPTERS` updated via `sync_wiring_marker` |
