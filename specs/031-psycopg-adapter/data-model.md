# Data Model: psycopg Async Driven Adapter

Entities generated into `src/<pkg>/infrastructure/driven_adapters/psycopg/`.

## PsycopgSettings (`psycopg_settings.py`)

Pydantic `BaseSettings`, `env_prefix="PSYCOPG_"`, `env_file=".env"`, `extra="ignore"`.

| Field | Type | Default | Env var | Rule |
|---|---|---|---|---|
| `database_url` | `str` | — (required) | `PSYCOPG_DATABASE_URL` | Missing value fails at startup |
| `min_size` | `int` | `1` | `PSYCOPG_MIN_SIZE` | Minimum pooled connections |
| `max_size` | `int` | `10` | `PSYCOPG_MAX_SIZE` | Maximum pooled connections |
| `timeout` | `float` | `30.0` | `PSYCOPG_TIMEOUT` | Seconds to open the pool and to wait for a free connection |

Provided by `@wireup.injectable def psycopg_settings_factory() -> PsycopgSettings`.

## PsycopgConnectionPool (`psycopg_config.py`)

Lazy wrapper over `psycopg_pool.AsyncConnectionPool`.

| Attribute | Type | Initial |
|---|---|---|
| `_settings` | `PsycopgSettings` | injected |
| `_lock` | `asyncio.Lock` | new lock |
| `_pool` | `AsyncConnectionPool[AsyncConnection[tuple[Any, ...]]] \| None` | `None` |

State transitions:

```text
           first connection()                      close()
 CLOSED ──────────────────────────▶ OPEN ───────────────────────▶ CLOSED
   ▲   open fails (PoolTimeout):         _pool stays set until close()
   └── _pool stays None; next connection() retries with a new pool
```

Operations:
- `connection()` — async context manager: ensure open (once, under `_lock`), then yield a connection from the pool; commit on success, rollback on error, always return it.
- `close()` — close the stored pool if any; no-op when never opened.

## psycopg_pool resource (`psycopg_config.py`)

`@wireup.injectable async def psycopg_pool(settings: PsycopgSettings) -> AsyncIterator[PsycopgConnectionPool]` — yields one wrapper per container and closes it when the container closes.

## PsycopgRepository (`psycopg_repository.py`)

| Member | Signature | Behavior |
|---|---|---|
| `__init__` | `(self, pool: PsycopgConnectionPool) -> None` | stores the wrapper |
| `ping` | `async (self) -> bool` | runs `SELECT 1`, returns `True` when the row is `(1,)` |
| `find_by_id` (commented example) | `async (self, item_id: int) -> <Model> \| None` | `cursor(row_factory=dict_row)`, `%s` parameter, maps row by column name |

Registration: `@wireup.injectable` without a gateway; `@wireup.injectable(as_type=<Gateway>)` and inheritance from `<Gateway>` with `--gateway`.
