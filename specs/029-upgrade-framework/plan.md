# Implementation Plan: Upgrade framework in `scaffold up`

**Branch**: `feature/029-upgrade-framework` | **Date**: 2026-11-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-upgrade-framework/spec.md`

---

## Summary

Add a registry-driven **upgrade action** framework invoked from `scaffold up`, with the first action migrating dependency-injector projects to the wireup layout (spec 028). Actions run before `uv lock --upgrade` and `uv sync`. Content-based `applies()` gates replace version filters. Dry-run emits unified diffs; JSON report splits stdout/stderr. Migration verification and skill installation are out of band (`install-skill`, skill checklist). Spec 028 docs are amended to exempt `up` from the legacy guard and to fix broken `docs/spec-029-migrate-di` links.

---

## Technical Context

**Language/Version**: Python 3.13+

**Primary Dependencies**:
- Existing: `typer`, `rich`, `Jinja2`, `tomli`/`tomllib`
- New: `libcst` (scaffolder; lazy import inside DI action)

**Storage**: N/A (CLI code generator)

**Testing**: `pytest`; static 0.5.0 fixture tree; golden JSON/diff snapshots

**Target Platform**: macOS / Linux with `uv`

**Project Type**: CLI scaffolder

**Constraints**: No new top-level `migrate-di` command; unify subprocess failures to exit `1`; do not run quality gates in `up`

**Scale/Scope**: New package `factory/upgrades/`, extend `update_project.py`, extend `FileWriter` dry-run, new `install-skill` command, 028 doc delta, skill tree `skills/migrate-di/`

**SC-001 measurement**: Count every line added, removed, or modified in the golden migration of the 0.5.0 fixture; automated changes must account for ≥ 70% of that total; pending-only lines count against automation (verified in T017).

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Assessment |
|-----------|------------|
| II — Tests | Add unit tests for registry order, `applies`, runner guards; integration test on 0.5.0 fixture; template tests if diff output touches builders. |
| III — Command surface | `up` extended with flags; new `install-skill` follows existing command registration patterns. |
| V — Test-first | Runner and DI action tests written before implementation. |
| VII — Branch naming | `feature/029-upgrade-framework` (flat numbered convention allowed). |

**Complexity**: libcst adds a dependency; justified by safe AST transforms (documented in research R8). Pre-existing `up` exit code `2` on uv failure is replaced with `1` (behavior change, scoped to this feature).

---

## Project Structure

### Documentation (this feature)

```text
specs/029-upgrade-framework/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── upgrade-actions.md
│   └── pending-items.md
├── tasks.md
└── checklists/
    └── requirements.md
```

### Source Code (target layout)

```text
src/scaffold_ca_python/
├── factory/
│   └── upgrades/
│       ├── __init__.py          # UPGRADE_ACTIONS, get_action_registry
│       ├── base.py              # UpgradeAction ABC
│       ├── runner.py            # UpgradeRunner
│       └── actions/
│           └── upgrade_2026_11_20_dependency_injector_to_wireup.py
├── commands/
│   ├── update_project.py        # orchestration + flags
│   └── install_skill.py         # migrate-di skill copy
├── core/
│   └── file_writer.py           # unified diff in dry-run
└── skills/
    └── migrate-di/              # packaged skill

tests/
├── factory/upgrades/
├── commands/test_update_project.py
├── commands/test_install_skill.py
└── fixtures/legacy_050_project/   # static 0.5.0 tree
```

**Structure Decision**: Mirror `factory/entry_points/` registry pattern (M5); runner lives beside actions, not under `commands/`.

---

## Phase 0 — Research

Delivered in [research.md](research.md) (content-based detection, execution order, exit codes, skill split).

---

## Phase 1 — Design

- Contracts: [contracts/upgrade-actions.md](contracts/upgrade-actions.md), [contracts/pending-items.md](contracts/pending-items.md)
- Entities: [data-model.md](data-model.md)
- Manual validation: [quickstart.md](quickstart.md)

---

## Phase 2 — Implementation outline (see tasks.md)

1. **Framework**: ABC, registry, runner with `persist_and_format` between actions; version guard.
2. **DI action**: libcst codemod, pyproject rewrite, fingerprint store for 0.5.0 composition files.
3. **CLI**: Flags on `up`; stderr/stdout split for JSON; `--skip-upgrades`, `--allow-dirty`.
4. **Diffs**: `FileWriter` accumulates patches for dry-run.
5. **Skill**: Wheel package + `install-skill` command + migration guide doc.
6. **028 delta**: FR-020, generated-files contract, link rewrites, delete obsolete `contracts/migrate-di.md`, update `_LEGACY_MIGRATION_HINT`.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| libcst runtime dep | Safe container and import transforms | Regex codemod unsafe at SC-001 coverage |
| Changes published 028 specs | H6/H7 link rot and wrong `up` legacy rule | Leaving 028 wrong blocks migration discoverability |