# Tasks: psycopg Async Driven Adapter

**Input**: Design documents from `specs/031-psycopg-adapter/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅, quickstart.md ✅

**Organization**: Tasks grouped by user story. Tests are written first and must fail before the matching implementation (Constitution Principle V). Test names, docstrings and template comments MUST NOT contain Spec Kit IDs (`T0xx`, `FR-0xx`, `US1`…): `tests/test_source_hygiene.py` rejects them (Principle VIII).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)

---

## Phase 1: Setup

- [X] T001 Add `PSYCOPG_POOL = "psycopg-pool~=3.3.3"` to `src/scaffold_ca_python/factory/dependencies.py` next to `PSYCOPG_BINARY` (re-check the latest 3.3.x on PyPI first); keep it a separate requirement, never the `psycopg[...,pool]` extra (research R-4)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Register the new type so every story can invoke `scaffold gda --type psycopg`.

### Tests (write first, verify they FAIL)

- [X] T002 [P] Update `tests/factory/test_registry.py`: add `"psycopg"` to the expected set in `test_driven_adapter_registry_keys` and assert `da["psycopg"].fixed_name == "psycopg"` in the fixed-name test
- [X] T003 [P] Add `"psycopg"` to the allowed-types loop of `test_gda_unknown_type` in `tests/commands/test_behavior_contract.py`

### Implementation

- [X] T004 Create `src/scaffold_ca_python/factory/driven_adapters/da_psycopg.py` with `DrivenAdapterPsycopg(DrivenAdapterFactory)`: `description = "Async PostgreSQL with raw SQL (psycopg 3 pool)"`, `fixed_name = "psycopg"`, `template_pkg = "driven_adapter/psycopg"`, `src_files` = (`__init__.py`, `psycopg_settings.py`, `psycopg_config.py`, `psycopg_repository.py`), `test_files` = (`test_psycopg_adapter.py`), `runtime_dependencies = (PSYCOPG_BINARY, PSYCOPG_POOL, PYDANTIC_SETTINGS)`; register `"psycopg": DrivenAdapterPsycopg` in `DRIVEN_ADAPTER_FACTORIES` (`src/scaffold_ca_python/factory/driven_adapters/__init__.py`)

**Checkpoint**: T002 and T003 green.

---

## Phase 3: User Story 1 — Generate psycopg Adapter (Priority: P1) 🎯 MVP

**Goal**: `scaffold gda --type psycopg` generates a lazily opened async pool, settings, repository and a database-free test, passing all quality checks.

**Independent Test**: `uv run pytest tests/factory/driven_adapters/test_da_psycopg.py tests/templates/test_driven_adapter_templates.py tests/commands/test_generate_driven_adapter.py tests/factory/test_dry_run_parity.py --no-cov`

### Tests for US1 (write first, verify they FAIL)

- [X] T005 [P] [US1] Create `tests/factory/driven_adapters/test_da_psycopg.py` (model it on `test_da_sqlalchemy.py`): (a) dry-run preview contains the four source files, `test_psycopg_adapter.py` and `src/tests/conftest.py`; (b) after `persist()`, `[project.dependencies]` contains `psycopg[binary]`, `psycopg-pool` and `pydantic-settings` and no `[dependency-groups]` entry was added; (c) `conftest.py` contains `psycopg_env` and `PSYCOPG_DATABASE_URL`; (d) when `pyproject.toml` already declares `psycopg[binary]~=3.3.9`, `psycopg-pool` is still injected
- [X] T006 [P] [US1] Add a `# psycopg` block to `tests/templates/test_driven_adapter_templates.py` rendering each template with `_ctx()`: settings → `class PsycopgSettings`, `env_prefix="PSYCOPG_"` when rendered with `_ctx("psycopg")`, fields `database_url: str`, `min_size: int = 1`, `max_size: int = 10`, `timeout: float = 30.0`; config → `AsyncConnectionPool(`, `open=False`, `asyncio.Lock()`, `open(wait=True`, `_pool: AsyncConnectionPool[AsyncConnection[tuple[Any, ...]]] | None = None`, and the `__init__` body does not construct `AsyncConnectionPool`; config also yields from the opened pool's `pool.connection()`; repository → `SELECT 1`, `dict_row`, `%s`, and none of `f"SELECT`, `f'SELECT`, `.format(` or `" % (` (no string-formatted SQL); test template → `AsyncConnectionPool` is patched and there is a test for retry after a failed open
- [X] T007 [P] [US1] Add to `tests/commands/test_generate_driven_adapter.py`: `--dry-run` output includes `driven_adapters/psycopg`, `psycopg_config` and `psycopg-pool`; `gda --type psycopg --driver sqlite` exits 1 with "only valid with --type sqlalchemy"; running `gda --type psycopg` twice leaves exactly one `psycopg_env` in `conftest.py`; `gda --help` lists `psycopg` and the `--type psycopg --gateway` example
- [X] T008 [P] [US1] Add `("psycopg", None)` to the `test_gda_dry_run_parity` parametrization in `tests/factory/test_dry_run_parity.py` with a `ModuleContext(name="psycopg", …)` branch

### Implementation for US1

- [X] T009 [P] [US1] Create `src/scaffold_ca_python/templates/driven_adapter/psycopg/__init__.py.jinja2` (module docstring only, as in the sqlalchemy group)
- [X] T010 [P] [US1] Create `psycopg_settings.py.jinja2`: `PsycopgSettings(BaseSettings)` with `database_url: str`, `min_size: int = 1`, `max_size: int = 10`, `timeout: float = 30.0`, `SettingsConfigDict(env_prefix="{{ module_name | upper }}_", env_file=".env", env_file_encoding="utf-8", extra="ignore")`, docstring with a `postgresql://user:password@localhost:5432/mydb` example; `@wireup.injectable def psycopg_settings_factory() -> PsycopgSettings`
- [X] T011 [P] [US1] Create `psycopg_config.py.jinja2`: `PsycopgConnectionPool` per data-model.md — `_ensure_open()` builds a new `AsyncConnectionPool(self._settings.database_url, min_size=…, max_size=…, timeout=…, open=False)` under `self._lock` only while `self._pool is None`, awaits `open(wait=True, timeout=self._settings.timeout)` and stores the pool only on success (a one-line *why* comment cites that a failed pool cannot be reopened); `connection()` is an `@asynccontextmanager` yielding from `self._pool.connection()`; `close()` closes the stored pool if any; resource `@wireup.injectable async def psycopg_pool(settings: PsycopgSettings) -> AsyncIterator[PsycopgConnectionPool]` with `await pool.close()` in `finally`
- [X] T012 [P] [US1] Create `psycopg_repository.py.jinja2`: `PsycopgRepository.__init__(self, pool: PsycopgConnectionPool)`; `async def ping(self) -> bool` running `SELECT 1` through `async with self._pool.connection() as conn, conn.cursor() as cur` and returning `await cur.fetchone() == (1,)`; commented `find_by_id` using `conn.cursor(row_factory=dict_row)`, `"... WHERE id = %s", (item_id,)` and a *why* comment against string-formatted SQL; reuse the `{% if gateway %}` import / `@wireup.injectable(as_type=…)` / inheritance block from `sqlalchemy_repository.py.jinja2`
- [X] T013 [US1] Create `test_psycopg_adapter.py.jinja2` (no server, `unittest.mock` only): repository `ping()` returns `True` and executes `SELECT 1` with a fake wrapper whose `connection()` is an async context manager; wrapper tests patching `{{ project.python_package }}.infrastructure.driven_adapters.psycopg.psycopg_config.AsyncConnectionPool` — constructing the wrapper does not create a pool; two concurrent first uses (`asyncio.gather`) create and open exactly one pool; `connection()` delegates to the patched pool's `connection()` context (which owns commit/rollback/return); a first `open` raising `PoolTimeout` leaves no pool and the next use creates a new one; `close()` closes the opened pool and is a no-op when never opened; the resource closes the wrapper on exit
- [X] T014 [US1] Implement `DrivenAdapterPsycopg.build_extra` with `@override`: `self.append_env_fixture(builder, resolve_tests_root(builder.project_root) / "conftest.py", "psycopg_env", _CONFTEST_FIXTURE)` where `_CONFTEST_FIXTURE` sets `PSYCOPG_DATABASE_URL` to `postgresql://user:password@localhost:5432/test` (contract)
- [X] T015 [US1] Add the `"gda:psycopg"` entry to `tests/factory/fixtures/dry_run_baseline.json` with the sorted list from `contracts/generated-files.md`
- [X] T016 [US1] Update `src/scaffold_ca_python/commands/generate_driven_adapter.py`: `--type` help lists `psycopg`; `_GDA_EPILOG` gains `* scaffold gda --type psycopg --gateway book_repository`
- [X] T017 [US1] Manual check (quickstart scenario 1) in `$CLAUDE_JOB_DIR/tmp`: generate, `uv sync`, `uv run pytest` (template coverage gate on), `uv run mypy --strict src`, `uv run ruff check .`, `scaffold vs`

**Checkpoint US1**: Independent Test command green; manual check green with no database.

---

## Phase 4: User Story 2 — Gateway Integration (Priority: P1)

**Goal**: `--gateway` binds the repository to a domain port and keeps the wiring test green without a database.

**Independent Test**: `uv run pytest tests/factory/driven_adapters/test_da_psycopg.py -k gateway --no-cov` and e2e scenario `14_psycopg_gateway`.

### Tests for US2 (write first, verify they FAIL)

- [X] T018 [P] [US2] Add to `tests/factory/driven_adapters/test_da_psycopg.py`: with a `gateway` param (`book_repository` / `BookRepository` / `book`), the repository renders `@wireup.injectable(as_type=BookRepository)` and `class PsycopgRepository(BookRepository)`, and `test_wiring.py` gains `test_container_resolves_psycopg`
- [X] T019 [P] [US2] Add `_scenario_14_psycopg_gateway` to `tests/e2e/test_generated_project_quality.py` (`gm --name book`, `guc --name get_book --uses book_repository`, `gda --type psycopg --gateway book_repository`, `gep --type restapi`) and register it in `_SCENARIOS`

### Implementation for US2

- [X] T020 [US2] Make T018 and T019 green; only template fixes in `psycopg_repository.py.jinja2` are expected, since `append_wiring_test` and `sync_wiring_marker` already handle gateways

**Checkpoint US2**: T018 and scenario 14 green.

---

## Phase 5: User Story 3 — Coexistence and Cleanup (Priority: P2)

**Goal**: `rest-consumer`, `sqlalchemy` and `psycopg` share one `conftest.py`; `dm psycopg` removes only its fixture.

**Independent Test**: `uv run pytest tests/commands/test_behavior_contract.py --no-cov` and e2e scenario `15_psycopg_with_sqlalchemy`.

### Tests for US3 (write first, verify they FAIL)

- [X] T021 [P] [US3] Add to `tests/commands/test_behavior_contract.py`: generating `rest-consumer`, `sqlalchemy` and `psycopg` yields one `from __future__ import annotations` and all three fixtures, and `ast.parse` succeeds; `dm --name psycopg --confirm` removes `psycopg_env` and keeps `rest_consumer_env` and `sqlalchemy_env`
- [X] T022 [P] [US3] Add `_scenario_15_psycopg_with_sqlalchemy` to `tests/e2e/test_generated_project_quality.py` (`gda --type sqlalchemy`, `gda --type psycopg`, assert `psycopg-pool` in `pyproject.toml`, `dm --name psycopg --confirm`, assert `sqlalchemy_env` kept and `psycopg_env` gone) and register it

### Implementation for US3

- [X] T023 [US3] Add `"psycopg": "psycopg_env"` to `_CONFTEST_FIXTURE_NAMES` in `src/scaffold_ca_python/factory/simple/delete_module_factory.py`

**Checkpoint US3**: T021 and scenario 15 green.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T024 [P] Update `README.md`: add `psycopg` to the Features list, the `gda` row of the command table and the generated-projects tech-stack table; add a `#### psycopg async adapter` subsection after the SQLAlchemy one covering when to choose it over `sqlalchemy`, `PSYCOPG_DATABASE_URL`/`PSYCOPG_MIN_SIZE`/`PSYCOPG_MAX_SIZE`/`PSYCOPG_TIMEOUT`, the lazily opened pool, and a `%s`-parameter example
- [X] T025 [P] Update `.specify/memory/constitution.md` (v2.2.1, PATCH): stop enumerating `gda`/`gep` types in the Principle III table, point to `scaffold gda --help` / `scaffold gep --help`, and name `DRIVEN_ADAPTER_FACTORIES` / `ENTRY_POINT_FACTORIES` as the single source of truth, so `psycopg` and future types need no amendment
- [X] T026 Run `uv run ruff check src tests`, `uv run ruff format --check src tests`, `uv run mypy --strict src`; fix any finding
- [X] T027 Run `uv run pytest` (coverage ≥ 80 %); fix regressions
- [X] T028 Run `UV_SYSTEM_CERTS=1 uv run pytest -m e2e --no-cov -rs`; all scenarios, including 14 and 15, pass
- [X] T029 Run quickstart scenarios 2–4 manually and record any deviation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none
- **Foundational (Phase 2)**: depends on T001; blocks all stories
- **US1 (Phase 3)**: depends on Phase 2
- **US2 (Phase 4)**: depends on T012 (repository template) from US1
- **US3 (Phase 5)**: depends on T014 (conftest fixture) from US1
- **Polish (Phase 6)**: depends on all stories

### Within Each Story

- T005–T008 fail before T009–T016
- T018–T019 fail before T020
- T021–T022 fail before T023

### Parallel Opportunities

- T002, T003 (different test files)
- T005, T006, T007, T008 (different test files)
- T009, T010, T011, T012 (different templates)
- T019 and T022 touch the same e2e file: write them sequentially
- T024, T025 (different docs)

---

## Implementation Strategy

### MVP First (US1 only)

1. Phases 1–2
2. Phase 3 (T005–T017)
3. **Stop and validate**: Independent Test command + manual check with no database

### Incremental Delivery

1. Setup + Foundational → type registered
2. US1 → generation works standalone
3. US2 → gateway binding (scenario 14)
4. US3 → coexistence and cleanup (scenario 15)
5. Polish → docs, constitution PATCH, full suites

## Notes

- Commit only when the user asks.
- `UV_SYSTEM_CERTS=1` is a local workaround only; never add it to code or CI.
