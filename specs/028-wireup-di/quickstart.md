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

## Scenario 4: Migration of a 0.5.0 project (SC-002, SC-005)

```bash
# Use the test fixture
cp -r tests/fixtures/legacy_project_050 /tmp/legacy-migration-test
cd /tmp/legacy-migration-test && git init && git add . && git commit -m "baseline"

# Dry run — must write nothing
uv run scaffold migrate-di --dry-run
# Verify no changes
git diff --exit-code && echo "DRY-RUN OK"

# Apply
uv run scaffold migrate-di --yes --report json | tee /tmp/migration-report.json

# Check exit code
echo "Exit: $?"   # expect 1 (applied, no pending) or 2 (applied, with pending)

# Automated items should include pyproject update, container→factories, @injectable insertions
cat /tmp/migration-report.json | python3 -c "import json,sys; r=json.load(sys.stdin); print('Automated:', len(r['automated']), '| Pending:', len(r['pending']))"
```

**Expected**:
- At least 70% of changes are in the `automated` list.
- Every pending item has `kind`, `file`, `line`, `guide_section`.
- Project's own suite runs after migration (output shown by the command).

---

## Scenario 5: Agent skill installation and alignment test

```bash
# From the scaffolder repo root
uv run scaffold migrate-di --install-skill --dry-run  # should print install plan, write nothing

# Install into the demo-app from Scenario 1
cd /tmp/demo-app
uv run scaffold migrate-di --install-skill
ls .claude/skills/migrate-di/   # SKILL.md, references/
ls .cursor/skills/migrate-di/
ls .agents/skills/migrate-di/
grep "migrate-di" AGENTS.md

# Alignment test (in the scaffolder repo)
cd /path/to/scaffold-repo
uv run pytest tests/templates/test_skill_alignment.py -v
```

**Expected**: three skill directories created; `AGENTS.md` has the reference line; alignment test passes.

---

## Scenario 6: Agent follows the skill (manual acceptance, documented)

Prerequisites: Scenario 4 completed and `--install-skill` run on the migrated project.

1. Open the project in Claude Code.
2. Type: "migrate this project to wireup using the installed skill."
3. Verify the agent:
   - reads `SKILL.md` first,
   - runs `scaffold migrate-di --dry-run` and summarises the diff,
   - asks for approval before running `scaffold migrate-di --yes`,
   - resolves pending items one by one using `references/recipes.md`,
   - asks for approval before any `git commit`.
4. Final check: `uv run ruff check . && uv run mypy --strict src/ && uv run pytest && uv run scaffold validate-structure` all pass.

**Expected**: agent completes without improvising; stops at every approval gate.

---

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
