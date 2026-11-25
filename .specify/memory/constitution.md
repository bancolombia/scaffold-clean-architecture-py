<!--
## Sync Impact Report

**Version change**: 1.0.0 → 2.0.0
**Type**: MAJOR — backward-incompatible reduction of Principle III command scope; new mandatory
constraint added to Principle II (`tests/templates/` directory).

### Modified principles
- **Principle II** — Added mandatory `tests/templates/` directory requirement with per-group
  rendering assertions (new bullet under the existing unit-test bullet).
- **Principle III** — Removed `gat`/`gpt` command rows (out of v1 scope); scoped `gda` types
  from 9 to 3 (`rest-consumer`, `secrets`, `generic`); scoped `gep` types from 8 to 4
  (`restapi`, `agent`, `mcp`, `generic`); `restapi` is now the canonical FastAPI entry-point
  type name (previously `rest-client`).

### Added sections
None.

### Removed sections
- `generate-acceptance-test` (`gat`) row from Principle III command table.
- `generate-performance-test` (`gpt`) row from Principle III command table.

### Templates requiring updates
| File | Status | Notes |
|---|---|---|
| `specs/004-scaffold-ca-python-cli/plan.md` | ✅ updated | Constitution Check: Principle II (tests/templates/ mandate) + Principle III (remove scoped note) |
| `specs/004-scaffold-ca-python-cli/spec.md` | ✅ updated | `rest-client` → `restapi` in US-5 and FR-009; `gep` supported types updated |
| `specs/004-scaffold-ca-python-cli/contracts/gep.md` | ✅ updated | All `rest-client` → `restapi`; `rest_client/` → `restapi/` directory names |
| `specs/004-scaffold-ca-python-cli/quickstart.md` | ✅ updated | `gep --type rest-client` → `gep --type restapi`; directory reference updated |
| `specs/004-scaffold-ca-python-cli/tasks.md` | ✅ updated | `rest-client` → `restapi` in Phase 6; T083–T089 added for `tests/templates/` |

### Deferred items
None — all placeholders resolved.

---

### Amendment v2.2.1 (2026-11-25) — PATCH
**Type**: PATCH — the command table stops enumerating types; no semantic change to governance.

**Changes**:
- Principle III: the `gda` and `gep` rows no longer list their types; they point to
  `scaffold gda --help` / `scaffold gep --help`. A new paragraph names the registries
  `DRIVEN_ADAPTER_FACTORIES` and `ENTRY_POINT_FACTORIES` as the single source of truth, so new
  adapter or entry-point types (e.g. `psycopg`, feature 031) need no amendment.

**Templates updated**: None.

---

### Amendment v2.2.0 (2026-11-24) — MINOR
**Type**: MINOR — new principle added.

**Changes**:
- Added **Principle VIII. Clean Code & Fast Tests**: comment rules (ruff `ERA` + hygiene
  tests), max 5 positional arguments (`PLR0917`), complexity ≤ 10 (`C90`), no unused
  arguments in `src/` (`ARG`), pytest idioms (`PT`), and real `uv` invocations confined to
  `tests/e2e/` behind `pytestmark = pytest.mark.e2e`. Every rule is backed by a tool;
  unmeasurable metrics are explicitly rejected.
- Argument-count rule uses `PLR0917` (positional only) instead of `PLR0913`: keyword-only
  parameters cannot be passed in the wrong order, and Typer callbacks expose one parameter
  per CLI option, so counting them all would force noqa exceptions.
- Principle III: `gda` types row now lists `sqlalchemy` (drift fix after feature 030).

**Templates updated**: None — `plan-template.md` derives its Constitution Check gates from this
file at runtime.

**Applied in the same branch** (`feature/031-clean-code-principle`):
- `pyproject.toml`: `[tool.ruff.lint] select` += `ERA`, `PT`, `PLR0917`, `ARG`;
  `per-file-ignores` `"tests/**" = ["ARG"]`; stale feature-022 comment removed.
- `tests/test_source_hygiene.py`: `test_real_uv_commands_only_in_e2e` and
  `test_e2e_modules_are_marked`.
- All 62 surfaced violations fixed; none left as pre-existing debt.

---

### Amendment v2.1.0 (2026-10-22) — MINOR
**Type**: MINOR — new governance clause (materially expanded guidance).

**Changes**:
- Governance: added "Pre-existing violations" clause. A feature MAY keep a violation that
  already existed on `main` if the plan documents it as pre-existing debt in Complexity
  Tracking and names a numbered follow-up feature whose spec directory exists before merge.
  New code introduced by a feature MUST still comply with every principle.

**Templates updated**: None. First applied by `specs/022-solid-code-cleanup/plan.md`.

---

### Amendment v2.0.3 (2026-04-10) — PATCH
**Type**: PATCH — branch naming exception; no semantic change to other governance rules.

**Changes**:
- Principle VII: Added exception bullet recognizing the project's established flat
  numbered-branch convention (`NNN-kebab-name`, e.g., `011-fix-restapi-cleanup`).
  The `feature/` prefix is not required for branches following this pattern.

**Templates updated**: None.

---

### Amendment v2.0.2 (2026-03-26) — PATCH
**Type**: PATCH — command rename; no semantic change to governance.

**Changes**:
- Principle III `generate-project` command renamed to `clean-architecture` per feature 007
  (CLI usability enhancements). The `ca` short alias is unchanged. The old `generate-project`
  name is a deprecated tombstone that exits 1 with a migration hint.

**Templates updated**: None — rename is surface-level only; no downstream template or
artifact structure was affected.

---

### Amendment v2.0.1 (2026-03-26) — PATCH
**Type**: PATCH — wording clarification only; no semantic change to governance.

**Changes**:
- Principle III `generate-project` table cell: removed "asyncio or sync" and "optional Pydantic
  models" (both contradicted FR-003 and FR-004); replaced with "async-only, Pydantic v2 domain
  models — no sync mode, no opt-out".
- Principle III `generate-pipeline` table cell: added Azure Pipelines alongside GitHub Actions
  to match FR-015 scope (no new commands or constraints added).

**Templates updated**: None — both changes correct stale table prose; no downstream template
or artifact structure was affected.
-->

# scaffold-ca-python Constitution

**Version**: 2.2.1 | **Ratified**: 2026-03-25 | **Last amended**: 2026-11-25

## Core Principles

### I. Clean Architecture in Generated Projects

Generated projects MUST follow a strict three-layer structure:

- **domain**: `model/` (pure data classes, no I/O) and `usecase/` (orchestration logic,
  depends only on the domain model and abstract ports).
- **infrastructure**: `entry-points/` (inbound adapters — web, messaging, CLI),
  `driven-adapters/` (outbound adapters — DB, HTTP, queues), `helpers/`
  (cross-cutting utilities with no business logic).
- **application**: composition root, dependency wiring, and runtime configuration.

**Dependency Rule (non-negotiable)**: outer layers MUST depend on inner layers; inner
layers MUST NOT import from outer layers. `domain` MUST NOT import from
`infrastructure` or `application`. `infrastructure` MAY import from `domain` only.

The `validate-structure` (`vs`) command MUST detect and report all dependency-rule
violations, flagging every `import` statement that crosses a layer boundary inward.

> **Scope note**: these constraints apply exclusively to projects *generated* by the
> CLI, not to the CLI tool's own source code.

**Rationale**: Enforcing the dependency rule at the tooling level prevents architectural
decay across all generated codebases and mirrors the guarantees provided by
[bancolombia/scaffold-clean-architecture](https://github.com/bancolombia/scaffold-clean-architecture).

---

### II. Template-Driven Code Generation

All source files emitted by any `generate-*` command MUST originate from Jinja2
templates located under `src/scaffold_ca_python/templates/`. Ad-hoc string
concatenation or f-string assembly for generated code is FORBIDDEN.

- Templates MUST be versioned alongside the CLI source.
- Templates MUST have dedicated unit tests that render them with representative inputs
  and assert structural correctness of the output.
- A `tests/templates/` directory MUST be present in the CLI test suite. It MUST contain
  at least one test per template group (one per subdirectory under
  `src/scaffold_ca_python/templates/`) that renders the template with representative
  context and asserts: (a) key class/function names are present, (b) import statements
  are correct, (c) async syntax is used where applicable.
- Template context objects MUST be validated via Pydantic models before rendering.

**Rationale**: A single rendering path eliminates inconsistencies between generated
artifacts and makes template changes auditable through standard code review.

---

### III. Full Command Parity with scaffold-clean-architecture

The CLI MUST implement the following commands (with required short aliases), adapted
for Python idioms:

| Command | Alias | Purpose |
|---|---|---|
| `clean-architecture` | `ca` | Scaffold full CA project (async-only, pyproject.toml, Pydantic v2 domain models — no sync mode, no opt-out) |
| `generate-model` | `gm` | Domain model class in `domain/model/` |
| `generate-use-case` | `guc` | Use-case class in `domain/usecase/` |
| `generate-driven-adapter` | `gda` | Driven adapter; supported types: `scaffold gda --help` |
| `generate-entry-point` | `gep` | Entry point; supported types: `scaffold gep --help` |
| `generate-helper` | `gh` | Utility helper module in `infrastructure/helpers/` |
| `generate-pipeline` | `gpipe` | CI/CD pipeline files (GitHub Actions or Azure Pipelines, via mandatory `--provider`) |
| `validate-structure` | `vs` | Validate CA layer boundaries and dependency rule |
| `delete-module` | `dm` | Safely delete a generated module |
| `update-project` | `up` | Update project dependencies to latest compatible versions |

Every command MUST support a `--dry-run` flag that previews all file changes without
writing to disk.

The adapter and entry-point types are not listed here: the registries
`DRIVEN_ADAPTER_FACTORIES` (`factory/driven_adapters/__init__.py`) and
`ENTRY_POINT_FACTORIES` (`factory/entry_points/__init__.py`) are the single source of truth.
They feed `--help`, `--type` validation and the tests, so adding a type MUST NOT require a
constitution amendment.

**Rationale**: Feature parity with the canonical Java/Gradle plugin ensures Python
teams can adopt the same architectural discipline with equivalent tooling.

---

### IV. Python-First Idioms

- Type hints MUST be present on all public interfaces in the CLI codebase.
- `ruff` MUST be the sole linter/formatter; PEP 8 compliance is enforced by CI.
- `mypy` MUST be enabled in strict mode for the CLI codebase.
- Async/await MUST be the default I/O pattern inside generated project skeletons.
- Python 3.13+ is the minimum supported runtime.
- `uv` MUST be used for dependency management, builds, and publishing.

**Rationale**: Enforcing modern Python idioms in both the tool and generated output
keeps the ecosystem coherent and eliminates common sources of technical debt.

---

### V. Test-First Development (NON-NEGOTIABLE)

Tests MUST be written before implementation code. The Red-Green-Refactor cycle is
strictly enforced:

1. Write a failing test that describes the desired behaviour.
2. Obtain explicit or implied acceptance that the test reflects intent.
3. Implement the minimum code to make the test pass.
4. Refactor under green.

- `pytest` is the test framework for the CLI codebase.
- `pytest-cov` MUST enforce a minimum 80% line-coverage gate; CI MUST fail below
  this threshold.
- Every `generate-*` command MUST produce a corresponding test scaffold file inside
  the generated project so that TDD is the default workflow for consumers.

**Rationale**: Testing discipline is non-negotiable because it is the primary quality
gate for a code-generation tool — generated code that ships broken tests undermines
the entire value proposition.

---

### VI. Developer Experience

- Every command MUST emit Rich-formatted output with progress indicators.
- Short aliases MUST be registered for every command (see Principle III table).
- Every command MUST support `--dry-run` to preview changes without writing to disk.
- All error messages MUST include a resolution hint that tells the user what to do
  next (e.g., "Run `scaffold-ca-python vs` to identify layer violations").
- `--help` output for every command MUST include at least one concrete usage example.

**Rationale**: The CLI is a productivity tool; poor UX discourages adoption and
negates the architectural benefits the tool is designed to enforce.

---

### VII. Git Workflow and Branch Naming

All feature branches MUST follow the convention:

```
feature/<branch-name>
```

- The separator MUST be a forward slash (`/`).
- `<branch-name>` MUST use lowercase kebab-case (e.g., `feature/generate-use-case`,
  `feature/jinja-template-engine`, `feature/fastapi-entry-point`).
- No other branch prefixes (`fix/`, `chore/`, `hotfix/`, etc.) are permitted without
  an explicit amendment to this constitution.
- **Exception (v2.0.3)**: This project uses a flat numbered-branch convention
  (`NNN-kebab-name`, e.g., `011-fix-restapi-cleanup`). The `feature/` prefix is not
  required for branches following this pattern.

**Rationale**: A single enforced branch pattern keeps CI selectors, code-review
automation, and project board filters simple and predictable.

---

### VIII. Clean Code & Fast Tests

Applies to the CLI tool's own source (`src/`) and test suite (`tests/`). Every rule in this
principle MUST be backed by an automated check; a rule without one MUST NOT be added here.

- **Comments**: comments MUST explain *why* (hidden constraint, workaround, non-obvious
  invariant), never restate *what* the code does. Commented-out code is FORBIDDEN (ruff
  `ERA`). Banner comments and Spec Kit task or requirement IDs (e.g., `T012`, `FR-003`) are
  FORBIDDEN in source, tests, and templates (`tests/test_source_hygiene.py`).
- **Function size**: functions MUST NOT take more than 5 positional arguments (ruff
  `PLR0917`); further parameters MUST be keyword-only (after `*`). Functions MUST stay at or
  below cyclomatic complexity 10 (ruff `C90`). Typer command callbacks follow the same rule:
  every CLI option after `ctx` is keyword-only.
- **Unused arguments**: FORBIDDEN in `src/` (ruff `ARG`). `tests/` is exempt because pytest
  fixtures are routinely requested only for their side effects.
- **Pytest idioms**: tests MUST follow pytest conventions (ruff `PT`): no composite
  assertions, no overly broad `pytest.raises`, tuple-style `parametrize` names.
- **Fast default run**: tests that invoke `uv` for real (`sync`, `run`, `add`, `lock`) or run
  quality toolchains on a generated project MUST live under `tests/e2e/`, and every test
  module there MUST declare `pytestmark = pytest.mark.e2e`, so the default `uv run pytest`
  excludes them. Enforced by `tests/test_source_hygiene.py`. Fast subprocess calls (e.g.,
  `git init`, `python -c`) and mocked `subprocess.run` remain allowed in unit tests.
- **Rejected metrics**: unmeasurable or arbitrary metrics (class-cohesion percentages, fixed
  per-test millisecond budgets, line-count caps without a linter rule) MUST NOT be adopted
  as MUST rules unless proposed together with an automated check.

**Rationale**: Rules enforced by ruff and pytest fail in pre-commit and CI regardless of who,
human or agent, wrote the code; prose-only rules drift. Keeping slow tests behind the `e2e`
marker preserves the fast feedback loop that Test-First Development (Principle V) depends on.

---

## Technology Stack

The following stack applies to the CLI tool itself:

| Concern | Tool |
|---|---|
| CLI framework | Typer |
| Terminal output | Rich |
| Code generation | Jinja2 |
| Package management / build / publish | uv |
| Linting / formatting | ruff |
| Static typing | mypy (strict) |
| Runtime validation (CLI internals) | Pydantic |
| Testing | pytest + pytest-cov |

Generated projects may optionally include any of the driven-adapter or entry-point
dependencies listed in Principle III, installed via `uv` at generation time.

## Governance

- This constitution supersedes all other practices, style guides, and verbal agreements.
- Any amendment MUST be proposed as a pull request against `.specify/memory/constitution.md`,
  include a rationale, and receive at least one explicit approval before merging.
- Version increments follow semantic versioning:
  - **MAJOR**: backward-incompatible governance changes, principle removals, or
    redefinitions that break existing workflows.
  - **MINOR**: new principles, new mandatory sections, or materially expanded guidance.
  - **PATCH**: clarifications, wording improvements, or typo fixes with no semantic change.
- All pull requests MUST include a Constitution Check section in their plan document
  verifying compliance with every applicable principle.
- **Pre-existing violations**: A feature MAY leave a violation of a principle in place only if
  all of the following hold:
  1. The violation existed on `main` before the feature branch was created (it is not
     introduced or worsened by the feature).
  2. The plan's Constitution Check marks the principle as "⚠️ pre-existing debt" and the
     Complexity Tracking table records the violation, its measured extent, and why fixing it
     is out of scope.
  3. A numbered follow-up feature (e.g. `023-error-hints`) is named in Complexity Tracking
     and its spec directory is created before the feature is merged.
  New code introduced by the feature MUST comply with every principle.
- Compliance reviews MUST occur at the start of each new feature branch and before
  merging to `main`.

**Version**: 2.2.1 | **Ratified**: 2026-03-25 | **Last Amended**: 2026-11-25
