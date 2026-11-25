# Quickstart: Validate the psycopg Adapter

**Prerequisites**: Python 3.13+, uv, a checkout of scaffold-ca-python on `feature/031-psycopg-adapter`. Scenario 6 also needs Docker. Behind a corporate proxy, export `UV_SYSTEM_CERTS=1` locally.

Set `S=/path/to/scaffold-clean-architecture-py` and work in an empty temporary directory.

## 1. Basic generation (US1)

```bash
uv run --project "$S" scaffold ca --name demo-pg && cd demo-pg
uv run --project "$S" scaffold gda --type psycopg --dry-run   # tree + pending deps, no writes
uv run --project "$S" scaffold gda --type psycopg
uv sync && uv run pytest && uv run mypy --strict src && uv run ruff check . && uv run --project "$S" scaffold vs
```

**Expected**: four source files and one test file as in [contracts/generated-files.md](contracts/generated-files.md); `psycopg[binary]`, `psycopg-pool` and `pydantic-settings` in `[project.dependencies]`; every check passes with no database running.

## 2. Gateway binding (US2)

```bash
uv run --project "$S" scaffold ca --name demo-gw && cd demo-gw
uv run --project "$S" scaffold gm --name book
uv run --project "$S" scaffold guc --name get_book --uses book_repository
uv run --project "$S" scaffold gda --type psycopg --gateway book_repository
uv sync && uv run pytest -q
```

**Expected**: `PsycopgRepository(BookRepository)` with `as_type=BookRepository`; `test_container_resolves_psycopg` passes; `MISSING_ADAPTERS` is empty.

## 3. Coexistence and cleanup (US3)

```bash
uv run --project "$S" scaffold gda --type rest-consumer
uv run --project "$S" scaffold gda --type sqlalchemy
uv run --project "$S" scaffold gda --type psycopg
python -c "import ast; ast.parse(open('src/tests/conftest.py').read())"
grep -c "from __future__ import annotations" src/tests/conftest.py   # → 1
uv run --project "$S" scaffold dm --name psycopg --confirm
grep -E "rest_consumer_env|sqlalchemy_env|psycopg_env" src/tests/conftest.py
```

**Expected**: one header; after `dm`, only `rest_consumer_env` and `sqlalchemy_env` remain; `psycopg-pool` was added even though `psycopg[binary]` already existed.

## 4. Error paths

```bash
uv run --project "$S" scaffold gda --type psycopg --driver sqlite   # exit 1, --driver is sqlalchemy-only
uv run --project "$S" scaffold gda --type psycopg --gateway nope    # exit 1, gateway not found + hint
```

## 5. Scaffold test suites

```bash
cd "$S"
uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy --strict src
uv run pytest
uv run pytest -m e2e --no-cov -k "psycopg"
```

**Expected**: all green; e2e scenarios `14_psycopg_gateway` and `15_psycopg_with_sqlalchemy` pass.

## 6. Optional: real PostgreSQL

```bash
docker run --rm -d -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres
export PSYCOPG_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/postgres
```

Calling `await PsycopgRepository(...).ping()` from the generated service returns `True`. Stop the container and the next query fails with a pool timeout within `PSYCOPG_TIMEOUT` seconds; start it again and the following query succeeds without restarting the service.
