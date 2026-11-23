# Tasks: SQLAlchemy Async Driven Adapter

**Input**: Design documents from `specs/030-sqlalchemy-adapter/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks grouped by user story. Tests written before implementation (TDD — Constitution Principle V). The prototype from `1dbaac4` is already ported to `feature/030-sqlalchemy-adapter`; these tasks complete, correct, and extend it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1, US2, US3)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the new dependency constant and verify baseline is green.

- [X] T001 Add `PSYCOPG_BINARY = "psycopg[binary]~=3.2.0"` to `src/scaffold_ca_python/factory/dependencies.py` (verify latest 3.2.x on PyPI; use the highest available 3.2.x patch)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared infrastructure that US1, US2, and US3 all depend on. Must complete before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### Foundational Tests (write first, verify they FAIL)

- [X] T002 Write failing test `test_conftest_header_written_once_with_two_adapters` asserting that generating rest-consumer then sqlalchemy produces a `conftest.py` with exactly one `from __future__ import annotations` line; add to `tests/commands/test_generate_driven_adapter.py`
- [X] T003 Write failing test `test_dm_sqlalchemy_removes_fixture_leaves_rest_consumer` asserting that `dm --name sqlalchemy --confirm` removes `sqlalchemy_env` and keeps `rest_consumer_env` in `src/tests/conftest.py`; add to `tests/commands/test_behavior_contract.py`
- [X] T004 [P] Write failing tests for `--driver` flag validation: `test_driver_flag_on_rest_consumer_exits_1`, `test_driver_unknown_value_exits_2` in `tests/commands/test_behavior_contract.py`

### Foundational Implementation

- [X] T005 Add `append_env_fixture(builder, conftest_path, fixture_name, fixture_body)` static method to `DrivenAdapterFactory` in `src/scaffold_ca_python/factory/driven_adapters/base.py`; it reads the existing file (if any) and omits the header block when `import pytest` is already present; it then delegates to `builder.append_to_file(conftest_path, content, marker=fixture_name)`
- [X] T006 Refactor `DrivenAdapterRestConsumer.build_extra` in `src/scaffold_ca_python/factory/driven_adapters/da_rest_consumer.py` to call `DrivenAdapterFactory.append_env_fixture` instead of the local `_append_rest_consumer_conftest`; remove local `_CONFTEST_HEADER` and `_append_rest_consumer_conftest` helpers (keeping `_CONFTEST_FIXTURE` and `_CONFTEST_MARKER`)
- [X] T007 Replace `DeleteModuleFactory._remove_rest_consumer_conftest_fixture` with a generic `_remove_conftest_fixture(tests_root, fixture_name)` in `src/scaffold_ca_python/factory/simple/delete_module_factory.py`; the method accepts `fixture_name` as parameter and uses it in the regex; update the `build` method to call `_remove_conftest_fixture(tests_root, "rest_consumer")` for rest_consumer and `_remove_conftest_fixture(tests_root, "sqlalchemy")` for sqlalchemy
- [X] T008 Add `DbDriver` StrEnum (`postgresql`, `sqlite`) and `--driver: Optional[DbDriver] = None` Typer option in `src/scaffold_ca_python/commands/generate_driven_adapter.py`; add validation: if `type_` != `"sqlalchemy"` and `driver is not None` → `fail()` with exit code 1 explaining restriction; if `type_ == "sqlalchemy"` and `driver is None` → resolve to `DbDriver.postgresql` and print "Driver: postgresql (default)"; pass resolved driver via `builder.add_param("driver", driver)`; also update `_GDA_EPILOG` in the same file to add `* scaffold gda --type sqlalchemy --gateway book_repository` and `* scaffold gda --type sqlalchemy --driver sqlite` examples (Constitution Principle VI — `--help` MUST include concrete usage examples)

**Checkpoint**: Foundational tests T002–T004 must be RED (failing) before T005–T008. After T005–T008 all four must be GREEN.

---

## Phase 3: User Story 1 — Basic Generation + Driver Selection (Priority: P1) 🎯 MVP

**Goal**: `scaffold gda --type sqlalchemy [--driver postgresql|sqlite]` generates a complete working adapter; zero manual edits needed.

**Independent Test**: `uv run pytest tests/factory/driven_adapters/test_da_sqlalchemy.py tests/commands/test_generate_driven_adapter.py tests/templates/test_sqlalchemy_templates.py -v --no-cov`

### Tests for US1 (write first, verify they FAIL)

- [X] T009 [P] [US1] Write failing tests for driver selection in `tests/factory/driven_adapters/test_da_sqlalchemy.py`: `test_sqlalchemy_driver_postgresql_adds_psycopg_binary` (driver=postgresql → psycopg[binary] in runtime deps), `test_sqlalchemy_driver_sqlite_adds_aiosqlite_to_runtime` (driver=sqlite → aiosqlite in runtime deps), `test_aiosqlite_always_in_test_group` (regardless of driver); also update the existing `test_sqlalchemy_dependencies_injected` (line 71) to assert aiosqlite in `[dependency-groups.test]` rather than `[project.dependencies]`, and assert psycopg[binary] in runtime for the default driver — this test will break after T018 without this fix (H2)
- [X] T009a [P] [US1] Update `test_sqlalchemy_injects_sqlalchemy_and_aiosqlite` in `tests/commands/test_generate_driven_adapter.py` (line 44): change assertion from `aiosqlite in runtime` to `aiosqlite in dependency-groups.test`; add assertion that `psycopg[binary]` is in runtime for the default postgresql driver — this test will break after T018 without this fix (H1)
- [X] T010 [P] [US1] Write failing tests for template structure in `tests/templates/test_sqlalchemy_templates.py` (new file — Constitution Principle II mandatory): `test_sqlalchemy_config_has_sessionmaker_expire_on_commit_false`, `test_sqlalchemy_models_has_declarative_base`, `test_sqlalchemy_repository_uses_sessionmaker`, `test_sqlalchemy_test_adapter_uses_staticpool`; render each template with a representative `ModuleContext` and assert the expected strings are present
- [X] T011 [P] [US1] Write failing test `test_sqlalchemy_files_include_models_in_dry_run` asserting `sqlalchemy_models.py` is in the dry-run preview; add to `tests/factory/driven_adapters/test_da_sqlalchemy.py`
- [X] T012 [P] [US1] Write failing test `test_dry_run_prints_sqlalchemy_models_path` asserting `sqlalchemy_models` appears in `--dry-run` output; add to `tests/commands/test_generate_driven_adapter.py`
- [X] T012a [P] [US1] Write failing test `test_sqlalchemy_conftest_idempotent` in `tests/commands/test_generate_driven_adapter.py`: run `gda --type sqlalchemy` twice on the same project root; assert that `sqlalchemy_env` appears exactly once in `src/tests/conftest.py` (SC-005)

### Implementation for US1

- [X] T013 [US1] Update `src/scaffold_ca_python/templates/driven_adapter/sqlalchemy/sqlalchemy_config.py.jinja2`: add `async_sessionmaker[AsyncSession]` injectable with `expire_on_commit=False`; the engine injectable is a generator resource `async def sqlalchemy_engine(settings: SQLAlchemySettings) -> AsyncIterator[AsyncEngine]` with `create_async_engine` and `await engine.dispose()` in `finally`; the sessionmaker injectable is `def sqlalchemy_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]` returning `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`
- [X] T014 [P] [US1] Create `src/scaffold_ca_python/templates/driven_adapter/sqlalchemy/sqlalchemy_models.py.jinja2`: define `class Base(DeclarativeBase): pass`; add a commented example of a simple ORM model extending Base (e.g., `class ExampleORM(Base): __tablename__ = "example"; id = mapped_column(Integer, primary_key=True)`); include a comment directing the developer to extend Base for their own models and to use a migration tool (e.g., Alembic) for schema management
- [X] T015 [P] [US1] Update `src/scaffold_ca_python/templates/driven_adapter/sqlalchemy/sqlalchemy_repository.py.jinja2`: replace the engine-based `__init__` with `def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None: self._sessions = sessions`; update `ping()` to use `async with self._sessions() as session: await session.execute(text("SELECT 1"))`; add a commented example method showing `async with self._sessions() as session:` pattern; keep the `{% if gateway %}` / `{% else %}` conditional for `@wireup.injectable(as_type=)` and class inheritance
- [X] T016 [P] [US1] Update `src/scaffold_ca_python/templates/driven_adapter/sqlalchemy/sqlalchemy_settings.py.jinja2`: ensure URL example in docstring/comment shows `postgresql+psycopg://user:password@host:5432/dbname` for the postgresql driver (the `env_prefix="SQLALCHEMY_"`, `extra="ignore"`, `echo: bool = False` fields should already be correct from the prototype)
- [X] T017 [US1] Update `src/scaffold_ca_python/templates/driven_adapter/sqlalchemy/test_sqlalchemy_adapter.py.jinja2`: use `create_async_engine("sqlite+aiosqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)` with `StaticPool` from `sqlalchemy.pool`; call `Base.metadata.create_all` via `await engine.run_sync(Base.metadata.create_all)`; assert `await repo.ping()` returns `True`; no mocks
- [X] T018 [US1] Update `src/scaffold_ca_python/factory/driven_adapters/da_sqlalchemy.py`: (a) add `sqlalchemy_models.py` to `src_files` after `sqlalchemy_config.py`; (b) change `runtime_dependencies` ClassVar to `(SQLALCHEMY, PYDANTIC_SETTINGS)` only (remove AIOSQLITE from here); (c) add `AIOSQLITE` to `test_group_dependencies`; (d) update `build_extra` to read `builder.get_param("driver", DbDriver.postgresql)`, then call `builder.add_dependency(PSYCOPG_BINARY)` for postgresql or `builder.add_dependency(AIOSQLITE)` for sqlite; (e) refactor to call `DrivenAdapterFactory.append_env_fixture(builder, conftest_path, "sqlalchemy_env", _CONFTEST_FIXTURE)`
- [X] T019 [US1] Update `tests/factory/fixtures/dry_run_baseline.json`: add `"src/my_app/infrastructure/driven_adapters/sqlalchemy/sqlalchemy_models.py"` to the `gda:sqlalchemy` list (between `sqlalchemy_config.py` and `sqlalchemy_repository.py`)

**Checkpoint US1**: `uv run pytest tests/factory/driven_adapters/test_da_sqlalchemy.py tests/commands/test_generate_driven_adapter.py tests/templates/test_sqlalchemy_templates.py tests/factory/test_dry_run_parity.py -v --no-cov` must be GREEN.

---

## Phase 4: User Story 2 — Gateway Integration (Priority: P1)

**Goal**: `--gateway` binds the adapter to a domain interface, updates wiring test and `MISSING_ADAPTERS`.

**Independent Test**: `uv run pytest tests/factory/driven_adapters/test_da_sqlalchemy.py::test_sqlalchemy_gateway_renders_as_type -v --no-cov` (and an updated version of this test after template changes in T015)

### Tests for US2 (verify existing test covers the updated template)

- [X] T020 [US2] Verify `test_sqlalchemy_gateway_renders_as_type` in `tests/factory/driven_adapters/test_da_sqlalchemy.py` still passes after T015 (template update changes `__init__` signature); update the test if the assertion about `@wireup.injectable(as_type=BookRepository)` and `class SQLAlchemyRepository(BookRepository)` needs updating to match the new template output
- [X] T021 [P] [US2] Write failing e2e test `test_11_sqlalchemy_gateway` in `tests/e2e/test_generated_project_quality.py`: scaffold a project with `gm book`, `guc get_book --model book`, `gda --type sqlalchemy --gateway book_repository`; call `uv_sync_project` then `run_quality_checks`; assert all pass

### Implementation for US2

- [X] T022 [US2] Verify the gateway code path in `sqlalchemy_repository.py.jinja2` renders correctly after T015 by running `test_sqlalchemy_gateway_renders_as_type` — no additional code changes expected if template gateway block is preserved

**Checkpoint US2**: T020, T021 must be GREEN.

---

## Phase 5: User Story 3 — Coexistence and Cleanup (Priority: P2)

**Goal**: rest-consumer + sqlalchemy share a valid `conftest.py`; `dm` removes only the sqlalchemy fixture.

**Independent Test**: generate both adapters → `ast.parse(conftest.py)` succeeds; run `dm sqlalchemy` → `sqlalchemy_env` gone, `rest_consumer_env` present.

### Tests for US3 (verify failing tests from Phase 2 are covered)

- [X] T023 [US3] Verify T002 test (`test_conftest_header_written_once_with_two_adapters`) is now GREEN after T005 and T006 changes
- [X] T024 [US3] Verify T003 test (`test_dm_sqlalchemy_removes_fixture_leaves_rest_consumer`) is now GREEN after T007 changes
- [X] T025 [P] [US3] Write failing e2e test `test_12_rest_consumer_and_sqlalchemy` in `tests/e2e/test_generated_project_quality.py`: scaffold a project, run `gda --type rest-consumer` then `gda --type sqlalchemy`, call `run_quality_checks`; assert all pass; then run `scaffold dm --name sqlalchemy --confirm` and assert project still passes quality checks

### Implementation for US3

- [X] T026 [US3] Verify that T005, T006, and T007 (Phase 2 implementation) are sufficient for conftest coexistence; run `uv run pytest tests/commands/test_generate_driven_adapter.py tests/commands/test_behavior_contract.py -v --no-cov` and confirm GREEN

**Checkpoint US3**: T023–T025 GREEN; `uv run pytest tests/ --no-cov -q` passes.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T027 [P] Update README.md: add a `gda --type sqlalchemy` subsection under the driven adapters section explaining `--driver {postgresql,sqlite}` (default postgresql), `SQLALCHEMY_DATABASE_URL` required env var, how to extend `Base` to add ORM models, and a note directing developers to set up Alembic or another migration tool independently
- [X] T028 Run full test suite: `uv run pytest --no-cov -q`; fix any regressions
- [X] T029 Run mypy strict on changed source files: `uv run mypy --strict src/scaffold_ca_python/factory/ src/scaffold_ca_python/commands/generate_driven_adapter.py`; fix any errors
- [X] T030 Run ruff: `uv run ruff check src tests && uv run ruff format --check src tests`; fix any issues
- [X] T031 Run e2e suite: `UV_SYSTEM_CERTS=1 uv run pytest -m e2e --no-cov -rs`; all scenarios (including 11 and 12) must pass

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1; BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2
- **US2 (Phase 4)**: Depends on Phase 3 (gateway template block is in T015)
- **US3 (Phase 5)**: Depends on Phase 2 (uses foundational fixes T005–T007)
- **Polish (Phase 6)**: Depends on all story phases

### Within Each Story

- Tests MUST be written and verified FAILING before the corresponding implementation task
- T009–T012 (failing tests) must precede T013–T018 (implementation)
- T020–T021 (failing tests) must precede T022 (implementation)
- T023–T025 (verify/failing tests) must precede T026 (implementation verify)

### Parallel Opportunities

- T009, T010, T011, T012 (Phase 3 tests) can be written in parallel
- T013, T014, T015, T016 (templates) can be developed in parallel (different files)
- T017, T018, T019 sequentially follow the templates (T017 and T018 can overlap)
- T021 and T025 (e2e tests) can be written in parallel once Phase 3 is green

---

## Parallel Example: User Story 1 Templates

```bash
# Write failing tests in parallel (T009–T012):
Task: test_sqlalchemy_driver_postgresql/sqlite in test_da_sqlalchemy.py
Task: template structure tests in tests/templates/test_sqlalchemy_templates.py
Task: test models in dry_run preview (test_da_sqlalchemy.py)
Task: test dry_run prints models path (test_generate_driven_adapter.py)

# Update templates in parallel (T013–T016 — different files):
Task: update sqlalchemy_config.py.jinja2 (sessionmaker + expire_on_commit)
Task: create sqlalchemy_models.py.jinja2 (Base + example)
Task: update sqlalchemy_repository.py.jinja2 (sessionmaker-based)
Task: update sqlalchemy_settings.py.jinja2 (URL example)
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Complete Phase 1: Setup (T001)
2. Complete Phase 2: Foundational (T002–T008)
3. Complete Phase 3: US1 (T009–T019)
4. **STOP and VALIDATE**: run targeted test suite; check dry-run baseline; run `scaffold gda --type sqlalchemy` manually

### Incremental Delivery

1. Phase 1 + 2 → foundational shared infra ready
2. Phase 3 → basic generation + driver selection works (MVP)
3. Phase 4 → gateway integration works
4. Phase 5 → coexistence + cleanup works
5. Phase 6 → README + full gate

---

## Notes

- `[P]` tasks operate on different files and have no sequential dependency on incomplete tasks in the same batch
- Each US phase is independently testable via its Checkpoint command
- The prototype from `1dbaac4` is already ported; these tasks update and extend it — do not start from scratch
- Avoid touching `tests/fixtures/` (ruff exclude rule)
- No `git add`, `git commit`, or `git push` during implementation
