# Implementation Plan: MCP Entry Point Health Check Route

**Branch**: `feature/mcp-health-check` | **Date**: 2026-10-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/027-mcp-health-check/spec.md`

## Summary

Make `gep --type mcp` always generate `infrastructure/entry_points/mcp_server/routes.py`.

- **Route**: `routes.py` exposes a synchronous `bind_routes(mcp)` that registers an async `health_check` custom route (`GET /api/v1/health` returns `{"status": "ok"}`) via `FastMCP.custom_route`.
- **Wiring**: The generated `app.py` calls `routes.bind_routes(mcp)` once at module level, right after creating `mcp`, so the route is in place before `start_server()` builds the MCP HTTP app and is never duplicated.
- **Tests**: The feature ships a generated `test_routes.py`, extends the generated `test_app.py`, and adds CLI-side template, factory, and dry-run-baseline tests.
- **Scope**: Two new Jinja2 templates and a small edit to `EntryPointMcp.build()`. No new dependencies, flags, or CLI surface.

## Technical Context

**Language/Version**: Python 3.13+ (no change)

**Primary Dependencies**:
- CLI: Typer, Rich, Jinja2, Pydantic v2 (unchanged).
- Generated project: the existing `mcp~=1.30.0` (`FastMCP.custom_route`) and `starlette~=1.6.0` (`Request`, `JSONResponse`, `TestClient`).
- `httpx` for `TestClient` is already a transitive dependency of `mcp`.
- **No new dependency.**

**Storage**: N/A

**Testing**:
- CLI: pytest + pytest-cov (≥ 80% gate), in `tests/templates/`, `tests/factory/entry_points/`, and `tests/factory/` (dry-run parity).
- Generated project: pytest with Starlette `TestClient`.

**Target Platform**: Cross-platform CLI; generated server runs under uvicorn (unchanged)

**Project Type**: Single project — CLI code generator (template + factory change)

**Performance Goals**: N/A (constant-time health response; CLI generation time unchanged)

**Constraints**:
- `bind_routes` MUST run before `mcp.streamable_http_app()` is called and exactly once per process. It is called at module level, not inside `start_server()` or `lifespan` ([research R2](./research.md#r2--when-to-call-bind_routesmcp)).
- Generated `routes.py`/`test_routes.py` MUST pass the generated project's `ruff` (`E`, `F`, `I`, `UP`, `ANN`; tests ignore `ANN`).
- MUST NOT change `tools.py.jinja2`, the `--add-tool` path, flags, dependencies, or overwrite policy.

**Scale/Scope**:
- 2 new templates and 3 modified files (`ep_mcp.py`, `app.py.jinja2`, `test_app.py.jinja2`).
- 1 fixture update and test additions in 2 CLI test files.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Result |
|---|---|---|
| I. Clean Architecture in Generated Projects | `routes.py` lives in `infrastructure/entry_points/mcp_server/` and imports only the MCP SDK and Starlette. `app.py` (application layer) imports it, the same way it imports `tools`. No inward-crossing imports. | ✅ PASS |
| II. Template-Driven Code Generation | New `routes.py.jinja2` and `test_routes.py.jinja2` live under `templates/entry_point/mcp/`, with rendering tests in `tests/templates/test_entry_point_templates.py`. They reuse the existing validated module context. | ✅ PASS |
| III. Full Command Parity | No command, alias, or `--type` added or changed. | ✅ PASS |
| IV. Python-First Idioms | The generated handler is `async`. `bind_routes` is fully typed (`-> None`). CLI changes are typed and keep ruff/mypy strict compliance. | ✅ PASS |
| V. Test-First Development | Failing template, factory, and baseline tests are written before the templates and the factory edit. The generated project gets the `test_routes.py` scaffold. | ✅ PASS (enforced in `/speckit-tasks` → `/speckit-implement`) |
| VI. Developer Experience | `--dry-run` previews both new files. No new error paths, so no new hints are needed. | ✅ PASS |
| VII. Git Workflow and Branch Naming | Branch `feature/mcp-health-check` follows `feature/<kebab-name>`. | ✅ PASS |

**Post-design re-check (after Phase 1)**: unchanged — all ✅. No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/027-mcp-health-check/
├── plan.md                    # This file
├── research.md                # Phase 0
├── data-model.md              # Phase 1
├── quickstart.md              # Phase 1
├── contracts/
│   └── generated-routes.md    # Phase 1 — generated HTTP + file contract
├── checklists/
│   └── requirements.md        # From /speckit-specify + /speckit-clarify
└── tasks.md                   # Phase 2 (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
src/scaffold_ca_python/
├── factory/entry_points/
│   └── ep_mcp.py                          # MODIFIED: always queue routes.py + test_routes.py; docstring updated
└── templates/entry_point/mcp/
    ├── routes.py.jinja2                   # NEW: bind_routes(mcp) + async health_check
    ├── test_routes.py.jinja2              # NEW: GET 200 {"status":"ok"}, POST 405
    ├── app.py.jinja2                      # MODIFIED: import routes; routes.bind_routes(mcp) after mcp creation
    └── test_app.py.jinja2                 # MODIFIED: health route present once after repeated start_server(); GET through start_server() → 200

tests/
├── factory/
│   ├── entry_points/test_ep_mcp.py        # MODIFIED: routes.py/test_routes.py queued (with and without optional flags)
│   └── fixtures/dry_run_baseline.json     # MODIFIED: gep:mcp gains the two new paths
└── templates/
    └── test_entry_point_templates.py      # MODIFIED: render tests for routes/test_routes; app/test_app assertions
```

`CHANGELOG.md` is generated by release-please from the commit message (e.g. `feat(mcp): ...`), so it is not edited by hand.

**Structure Decision**: Single-project CLI layout, the same as every prior feature. Changes stay inside `factory/entry_points/` and `templates/entry_point/mcp/` and their matching tests. `book_smcp/` is out of scope.

## Complexity Tracking

*No entries — Constitution Check reported no violations.*
