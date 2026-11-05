# Quickstart Validation Guide: Wireup DI Migration

**Feature**: 028-wireup-di

This guide describes how to validate that the feature works end-to-end. Run these scenarios after implementing all blocks (A–H) and before merging.

---

## Prerequisites

```bash
# From repo root, on branch feature/028-wireup-di
SSL_CERT_FILE=/etc/ssl/cert.pem uv sync
uv run ruff check . && uv run mypy src && uv run pytest
```

All three must pass before running the scenarios below.

---

## Scenario 1: New project, full wiring, zero manual edits (SC-001)

```bash
# In /tmp — outside the scaffolder repo
cd /tmp && rm -rf demo-app && mkdir demo-app && cd demo-app

uv run scaffold ca --name demo-app
uv run scaffold gm order                        # domain model
uv run scaffold guc --name create_order --uses order_repository
uv run scaffold gda --type generic --name in_memory_order --gateway order_repository
uv run scaffold gh --name id_generator
uv run scaffold gep --type restapi
```

**Expected**:
- `application/config/wiring.py` exists; contains `INJECTABLES` and `create_container()`.
- `application/config/usecases/create_order_usecase.py` exists; contains a factory with typed params.
- `infrastructure/driven_adapters/in_memory_order/in_memory_order_adapter.py` contains `@injectable(as_type=OrderRepository)`.
- `infrastructure/helpers/id_generator/id_generator.py` contains `@injectable`.
- No `*_container.py` files anywhere.
- `pyproject.toml` contains `wireup==2.13.0`, not `dependency-injector`.
- `pyproject.toml` contains `scaffold_version = "` (not `di = "wireup"`).

```bash
SSL_CERT_FILE=/etc/ssl/cert.pem uv sync
uv run ruff check .
uv run mypy --strict src/
uv run pytest
uv run scaffold validate-structure
```

**Expected**: all five pass with zero errors and zero violations.

### Rest-consumer QA re-test (T107, FR-033/FR-039)

Use the local scaffolder, not a published release. Set `REPO` to the absolute repository path, run `uv sync` there, and add its `.venv/bin` to `PATH`. Use a fresh temporary parent directory for each of the three runs:

```bash
export PATH="$REPO/.venv/bin:$PATH"
uv run scaffold ca --name ms_library
cd ms_library
uv sync
source .venv/bin/activate
uv run scaffold gm --name book
```

Run the four checks below immediately after `gm`, then after **each** command in the selected row:

| QA scenario | Next command | Final command |
|-------------|--------------|---------------|
| 1 | `uv run scaffold guc --name book` | `uv run scaffold gda --type rest-consumer` |
| 2 | `uv run scaffold guc --name book --uses book_repository` | `uv run scaffold gda --type rest-consumer --gateway book_repository` |
| 3 | `uv run scaffold gda --type rest-consumer --gateway book_repository` | `uv run scaffold guc --name book --uses book_repository` |

```bash
uv run pytest
uv run ruff check .
uv run mypy src/ms_library
uv run ruff format --check .
```

**Expected:** all four commands exit 0 at all nine milestones; coverage stays at or above 75%. In scenario 2, strict wiring xfail is expected only before the adapter exists. Do not edit generated files or apply formatter fixes during QA. Deactivate the environment and delete only the generated `ms_library` directory after collecting evidence.

**Re-test 3, 2026-10-30 (requested 17:18 -05:00): manual scope PASS (36/36); expanded regression FAIL.** All four commands above pass at all nine milestones. The additional `uv run mypy --strict src/` includes generated tests and fails on `capsys` typing in `src/tests/test_main.py`; all three E2E cases fail on that check. This does not certify the other quickstart scenarios or close T105.

Evidence: [QA scenario 1](../../docs/qa-report-escenario-01-ms_library.md#9-re-test--2026-10-30-t107), [QA scenario 2](../../docs/qa-report-escenario-02-ms_library.md#9-re-test--2026-10-30-t107), [QA scenario 3](../../docs/qa-report-escenario-03-ms_library.md#10-re-test--2026-10-30-t107).

Latest evidence: [QA scenario 1 round 2](../../docs/qa-report-escenario-01-ms_library.md#10-re-test-2--2026-10-30), [QA scenario 2 round 2](../../docs/qa-report-escenario-02-ms_library.md#10-re-test-2--2026-10-30), [QA scenario 3 round 2](../../docs/qa-report-escenario-03-ms_library.md#11-re-test-2--2026-10-30).

Round 3 evidence: [QA scenario 1](../../docs/qa-report-escenario-01-ms_library.md#11-re-test-3--2026-10-30), [QA scenario 2](../../docs/qa-report-escenario-02-ms_library.md#11-re-test-3--2026-10-30), [QA scenario 3](../../docs/qa-report-escenario-03-ms_library.md#12-re-test-3--2026-10-30), [expanded regression log](../../docs/.qa-logs/retest-2026-10-30-ronda-3/regresion-rest-consumer.log).

---

## Scenario 2: Entry points — no layer violation (SC-004)

```bash
# From the demo-app directory above, after Scenario 1
grep -r "from.*application.*Container" src/ && echo "VIOLATION" || echo "OK"
uv run scaffold validate-structure
```

**Expected**: no output for the grep (no layer violation); `validate-structure` reports zero violations.

Inspect `src/demo_app/infrastructure/entry_points/api/v1/rest_controller.py`:
- Must contain `Injected[` somewhere.
- Must NOT contain `from demo_app.application` or `Provide[`.

---

## Scenario 3: Fail fast on missing dependency (SC-003)

```bash
# In a new project with a use case but no adapter
cd /tmp && rm -rf fail-test && mkdir fail-test && cd fail-test
uv run scaffold ca --name fail-test
uv run scaffold gm order
uv run scaffold guc --name create_order --uses order_repository
# Intentionally do NOT generate the adapter
```

Start the container programmatically:

```python
# /tmp/fail-test/check.py
from fail_test.application.config.wiring import create_container
import asyncio

async def main():
    c = create_container()  # must raise here
    await c.close()

asyncio.run(main())
```

```bash
uv run python check.py
```

**Expected**: `WireupError` naming `order_repository` / `OrderRepository` — raised at container creation, not deferred.

---

> **Migration scenarios** (0.5.0 → wireup, agent skill): see [docs/spec-029-migrate-di/quickstart.md](../../docs/spec-029-migrate-di/quickstart.md).

---

## Intermediate State: Use Case Without Adapter

This scenario validates fail-fast behaviour (SC-003) and the developer hint (FR-035).

```bash
cd /tmp && rm -rf ms-library && mkdir ms-library && cd ms-library

uv run scaffold ca --name ms-library
uv run scaffold gm book
uv run scaffold guc --name book --uses book_repository
```

**After these three commands**:
- `ruff check .` → **green** (import order correct, FR-032)
- `guc` output includes a hint: `Next step: scaffold gda --type ... --gateway book_repository` (FR-035)
- `ruff format --check .` and `mypy --strict src/` → **green**
- `pytest` → **green**: wiring tests are reported as `xfailed` with reason `No adapter implements: BookRepository` (the underlying error is `WireupError: unknown dependency on BookRepository`, SC-003)

```bash
uv run scaffold gda --type generic --name book_repository_adapter --gateway book_repository
```

**After adding the adapter**:
```bash
uv run ruff check .                   # green
uv run mypy --strict src/             # green
uv run pytest                         # green; 0 xfailed; coverage ≥ 75%
uv run scaffold validate-structure    # green
```

---

## Regression Check

```bash
# From scaffolder repo root
uv run pytest --tb=short -q
```

All existing tests must continue to pass. No new test failures introduced.
