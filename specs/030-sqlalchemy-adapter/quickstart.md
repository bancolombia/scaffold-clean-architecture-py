# Quickstart Validation Guide: SQLAlchemy Async Driven Adapter

**Feature**: 030-sqlalchemy-adapter | **Date**: 2026-11-23

This guide describes how to manually validate the feature end-to-end after implementation.
All commands are run from a temporary directory; no changes to the scaffold repo itself.

---

## Prerequisites

- `scaffold-ca-python` installed from the feature branch (`uv tool install -e /path/to/repo`).
- `uv` available.
- (Optional) PostgreSQL reachable locally for step 5.

---

## Scenario 1: Basic generation + quality checks (US1)

```bash
# 1. Create a fresh project
scaffold ca --name demo-db
cd demo-db

# 2. Add a domain model
scaffold gm --name book

# 3. Generate the SQLAlchemy adapter (postgresql default)
scaffold gda --type sqlalchemy --dry-run   # preview only
scaffold gda --type sqlalchemy             # write files
# Expected output: "Driver: postgresql (default)"

# 4. Sync and run quality checks
uv sync
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/
uv run pytest --no-cov

# 5. Validate structure
scaffold vs
```

**Expected**: all commands exit 0.

---

## Scenario 2: sqlite driver

```bash
# From the same demo-db project (or a fresh one)
scaffold gda --type sqlalchemy --driver sqlite
# Expected output: "Driver: sqlite"
```

Check `pyproject.toml`:
- `aiosqlite~=...` in `[project.dependencies]`
- `psycopg[binary]` NOT present

Check `sqlalchemy_settings.py` URL example uses `sqlite+aiosqlite://...`.

---

## Scenario 3: Gateway binding (US2)

```bash
scaffold ca --name demo-gw
cd demo-gw
scaffold gm --name book
scaffold guc --name get_book --model book
scaffold gda --type sqlalchemy --gateway book_repository
uv sync
uv run pytest --no-cov
scaffold vs
```

Verify:
- `sqlalchemy_repository.py` contains `@wireup.injectable(as_type=BookRepository)` and `class SQLAlchemyRepository(BookRepository)`.
- `src/tests/application/config/test_wiring.py` contains `test_container_resolves_sqlalchemy`.

---

## Scenario 4: Coexistence with rest-consumer (US3)

```bash
scaffold ca --name demo-combo
cd demo-combo
scaffold gda --type rest-consumer
scaffold gda --type sqlalchemy
python3 -c "import ast; ast.parse(open('src/tests/conftest.py').read()); print('OK')"
```

Then delete the SQLAlchemy adapter:

```bash
scaffold dm --name sqlalchemy --confirm
python3 -c "import ast; ast.parse(open('src/tests/conftest.py').read()); print('OK')"
grep -c "rest_consumer_env" src/tests/conftest.py   # must be >= 1
grep -c "sqlalchemy_env" src/tests/conftest.py      # must be 0
```

---

## Scenario 5: Driver flag validation

```bash
# --driver with wrong type must exit 1
scaffold gda --type rest-consumer --driver postgresql
echo "Exit code: $?"   # expect 1

# Unknown driver value must exit 2
scaffold gda --type sqlalchemy --driver oracle 2>&1
echo "Exit code: $?"   # expect 2
```

---

## Scenario 6: Idempotence

```bash
scaffold ca --name demo-idem
cd demo-idem
scaffold gda --type sqlalchemy
scaffold gda --type sqlalchemy   # second run (should overwrite files, not duplicate conftest fixture)
grep -c "sqlalchemy_env" src/tests/conftest.py   # must be exactly 1
```

---

## Scenario 7 (Optional): PostgreSQL connectivity

Requires a local PostgreSQL instance.

```bash
docker run -d --name pg-test -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres
scaffold ca --name demo-pg
cd demo-pg
scaffold gda --type sqlalchemy
uv sync
SQLALCHEMY_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres \
  uv run python -c "
import asyncio
from my_app.infrastructure.driven_adapters.sqlalchemy.sqlalchemy_config import sqlalchemy_engine
from my_app.infrastructure.driven_adapters.sqlalchemy.sqlalchemy_settings import SQLAlchemySettings
import os

async def main():
    settings = SQLAlchemySettings()
    async for engine in sqlalchemy_engine(settings):
        from sqlalchemy import text
        async with engine.begin() as conn:
            result = await conn.execute(text('SELECT 1'))
            print('ping:', result.scalar())  # expect: ping: 1

asyncio.run(main())
"
docker stop pg-test && docker rm pg-test
```

---

## Artifact References

- File list: [contracts/generated-files.md](contracts/generated-files.md)
- Data model: [data-model.md](data-model.md)
- Research decisions: [research.md](research.md)
