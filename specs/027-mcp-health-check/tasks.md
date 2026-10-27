---

description: "Task list for MCP Entry Point Health Check Route"
---

# Tasks: MCP Entry Point Health Check Route

**Input**: Design documents from `/specs/027-mcp-health-check/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/generated-routes.md, quickstart.md

**Tests**: REQUIRED. Spec FR-007, FR-008, and FR-012 plus Constitution Principle V (Test-First, non-negotiable) apply. Every test task must be written first and confirmed **failing** before its implementation task.

**Organization**: Tasks are grouped by user story. US1 (route generated) and US2 (route wired in `app.py`) are both P1. US3 (generated test scaffold) is P2.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 (from spec.md)

## Path Conventions

- CLI source: `src/scaffold_ca_python/`
- CLI tests: `tests/`
- Template helpers already in `tests/templates/test_entry_point_templates.py`: `renderer`, `_tmpl(...)`, `_ctx()`, `_app_ctx(with_resources=..., with_prompts=...)`
- Factory helpers already in `tests/factory/entry_points/test_ep_mcp.py`: `_make_builder(tmp_path)`; generated paths are `tmp_path / "src" / "ms_demo" / "infrastructure" / "entry_points" / "mcp_server"` (src) and `tmp_path / "src" / "tests" / "infrastructure" / "entry_points" / "mcp_server"` (tests)

---

## Phase 1: Setup

**Purpose**: Confirm a green baseline before changing anything.

- [X] T001 Run `uv run pytest`, `uv run ruff check .` and `uv run mypy src` from the repo root and confirm all pass on `feature/mcp-health-check` before any change (record failures, if any, as pre-existing)

---

## Phase 2: Foundational

No foundational tasks. The feature reuses the existing `ModuleBuilder`, template renderer, module context, and `entry_point/mcp/` template group. No new models, primitives, or dependencies are needed (see plan.md "Technical Context").

---

## Phase 3: User Story 1 - Generated MCP server exposes a health check out of the box (Priority: P1) 🎯 MVP

**Goal**: `gep --type mcp` always emits `mcp_server/routes.py` with `bind_routes(mcp)` registering `GET /api/v1/health` → `{"status": "ok"}`.

**Independent Test**: Render `routes.py.jinja2` and build `EntryPointMcp` in dry-run. `routes.py` is queued, and its content matches `contracts/generated-routes.md` §2.

### Tests for User Story 1 (write first, must FAIL) ⚠️

- [X] T002 [P] [US1] Add `routes.py.jinja2` rendering tests in `tests/templates/test_entry_point_templates.py` (new section `# mcp — routes.py`) asserting the rendered output, via `renderer.render_string(_tmpl("entry_point/mcp/routes.py.jinja2"), _ctx().model_dump())`, contains:
  - `from __future__ import annotations`
  - `from mcp.server.fastmcp import FastMCP`
  - `from starlette.requests import Request`
  - `from starlette.responses import JSONResponse, Response` (sorted order)
  - `def bind_routes(mcp: FastMCP) -> None:` (sync, not `async def bind_routes`)
  - `@mcp.custom_route(name="health_check", path="/api/v1/health", methods=["GET"])`
  - `async def health_check(_request: Request) -> Response:`
  - `{"status": "ok"}` and `return JSONResponse(response_data)`
  - It does NOT contain `@inject` or `Provide`
- [X] T003 [P] [US1] Add `test_mcp_queues_routes_py` in `tests/factory/entry_points/test_ep_mcp.py`: with `_make_builder(tmp_path)` + `EntryPointMcp().build(builder)` + `builder.persist()`, assert `src_dir / "routes.py"` is in the preview. Add a parametrized variant over `with_resources`/`with_prompts` ∈ {True, False} (set via `builder.add_param(...)`, matching the existing resources/prompts tests in the same file) asserting `routes.py` is always queued (spec edge case "Optional primitives")

### Implementation for User Story 1

- [X] T004 [US1] Create `src/scaffold_ca_python/templates/entry_point/mcp/routes.py.jinja2` with exactly the content of `specs/027-mcp-health-check/contracts/generated-routes.md` §2. It has no Jinja variables; keep it a `.jinja2` template so it goes through the renderer, per Principle II. Ensure a trailing newline (makes T002 pass)
- [X] T005 [US1] In `src/scaffold_ca_python/factory/entry_points/ep_mcp.py` `EntryPointMcp.build()`, under `# Always-generated files` right after the `tools.py` `add_file`, add `builder.add_file(src_dir / "routes.py", builder.render(f"{base}/routes.py.jinja2", ctx_dict), template_name=f"{base}/routes.py.jinja2")`. Keep the default `overwrite=False`, same as `tools.py`. Add `- src/infrastructure/entry_points/mcp_server/routes.py` to the "Always queues" list in the `build()` docstring (makes T003 pass)
- [X] T006 [US1] Add `"src/my_app/infrastructure/entry_points/mcp_server/routes.py"` to the `"gep:mcp"` list in `tests/factory/fixtures/dry_run_baseline.json`, keeping alphabetical order (after `__init__.py`, before `tools.py`). Run `uv run pytest tests/factory/test_dry_run_parity.py` and confirm it passes

**Checkpoint**: `routes.py` is generated and its content is verified. US1 is demoable via `gep --type mcp --dry-run` (FR-001–FR-005, FR-010, FR-013).

---

## Phase 4: User Story 2 - Health route is wired into the composition root automatically (Priority: P1)

**Goal**: The generated `app.py` imports `routes` and calls `routes.bind_routes(mcp)` once at module level, right after `mcp` is created. Never inside `start_server()` or `lifespan` (clarification Q2, research R2).

**Independent Test**: Render `app.py.jinja2` for all `with_resources`/`with_prompts` combinations and assert the import, the call placement, and that `container.wire(...)` and `start_server()` are unchanged.

### Tests for User Story 2 (write first, must FAIL) ⚠️

- [X] T007 [US2] Add `app.py.jinja2` rendering tests in `tests/templates/test_entry_point_templates.py` (existing `# mcp — app.py` section), parametrized over `_app_ctx(with_resources=..., with_prompts=...)` ∈ all 4 combinations, asserting:
  - (a) `from <pkg>.infrastructure.entry_points.mcp_server import routes, tools` is present (for `_ctx()`, `<pkg>` is that context's `project.python_package`).
  - (b) `routes.bind_routes(mcp)` appears exactly once (`out.count(...) == 1`).
  - (c) its index is after `mcp: FastMCP = FastMCP(` and before `async def lifespan` and `def start_server`.
  - (d) the `container.wire(` block does not contain `routes`.
  - (e) the existing `resources`/`prompts` imports and `bind_*` awaits still render per flag.

### Implementation for User Story 2

- [X] T008 [US2] Edit `src/scaffold_ca_python/templates/entry_point/mcp/app.py.jinja2`:
  - Change `from {{ project.python_package }}.infrastructure.entry_points.mcp_server import tools` to `... import routes, tools`.
  - Add the line `routes.bind_routes(mcp)` immediately after `mcp: FastMCP = FastMCP("{{ project.name }}", stateless_http=True)`.
  - Leave `lifespan`, `container.wire(...)`, and `start_server()` untouched (makes T007 pass; FR-006). The result must match `contracts/generated-routes.md` §3.

**Checkpoint**: A generated server answers `GET /api/v1/health` with zero manual edits (SC-002).

---

## Phase 5: User Story 3 - Generated project ships a test for the health route (Priority: P2)

**Goal**: The generated project gets `test_routes.py` (GET 200 + body, POST 405) and an extended `test_app.py` (route present exactly once after repeated `start_server()`).

**Independent Test**: Generate an MCP project, `uv sync`, run its `test_routes.py` and `test_app.py`. Both pass, and `ruff check` is clean on `routes.py` and `test_routes.py`.

### Tests for User Story 3 (write first, must FAIL) ⚠️

- [X] T009 [P] [US3] Add `test_routes.py.jinja2` rendering tests in `tests/templates/test_entry_point_templates.py` (new section `# mcp — test_routes.py`) asserting the output contains:
  - `from <pkg>.infrastructure.entry_points.mcp_server.routes import bind_routes`
  - `from starlette.testclient import TestClient`
  - `FastMCP(`
  - `bind_routes(`
  - `.get("/api/v1/health")`, `== 200`, `{"status": "ok"}`
  - `.post("/api/v1/health")`, `== 405`
  - It does NOT contain `with TestClient` (the lifespan must not start, research R5) and does NOT import `<pkg>.application.app`
- [X] T010 [P] [US3] Add `test_app.py.jinja2` rendering tests in `tests/templates/test_entry_point_templates.py` (existing `# mcp — test_app.py` section) asserting two new test functions are rendered:
  - `test_health_route_registered_once`: its body calls `start_server()` at least twice and asserts that the count of routes with `path == "/api/v1/health"` in `server.routes[0].routes` equals 1 (research R6).
  - `test_health_route_reachable_through_start_server`: contains `TestClient(app_module.start_server())`, `.get("/api/v1/health")`, `== 200` and `{"status": "ok"}`, and does NOT contain `with TestClient`.
- [X] T011 [P] [US3] Add `test_mcp_queues_test_routes_py` in `tests/factory/entry_points/test_ep_mcp.py` asserting `test_dir / "test_routes.py"` is in the dry-run preview
- [X] T012 [US3] Add an end-to-end test `test_gep_mcp_generated_health_route_tests_pass` in `tests/commands/test_generate_entry_point.py`, reusing the existing `mcp_project` fixture and the `uv sync` → skip-on-failure pattern of `test_add_tool_creates_registration_test`:
  - Run `uv run pytest <test_routes.py> <test_app.py> -v --no-cov` in the generated project and assert `returncode == 0`.
  - Run `uv run ruff check <routes.py> <test_routes.py>` and assert `returncode == 0` (FR-009).
  - Use the same timeouts as the existing test.

### Implementation for User Story 3

- [X] T013 [US3] Create `src/scaffold_ca_python/templates/entry_point/mcp/test_routes.py.jinja2`:
  - Module docstring `"""Tests for {{ project.python_package }}.infrastructure.entry_points.mcp_server.routes."""`.
  - Imports: `from __future__ import annotations`, `from mcp.server.fastmcp import FastMCP`, `from starlette.testclient import TestClient`, `from {{ project.python_package }}.infrastructure.entry_points.mcp_server.routes import bind_routes` (ruff `I` order).
  - Helper `_client() -> TestClient`: builds `FastMCP("test")`, calls `bind_routes(mcp)`, returns `TestClient(mcp.streamable_http_app())`, with no `with` block.
  - `test_health_check_returns_ok`: GET returns 200, and `response.json() == {"status": "ok"}`.
  - `test_health_check_rejects_post`: POST returns 405.
  - Makes T009 pass.
- [X] T014 [US3] Edit `src/scaffold_ca_python/templates/entry_point/mcp/test_app.py.jinja2` to append `test_health_route_registered_once`:
  - Call `app_module.start_server()` twice and keep the second result as `server`.
  - Assert `[r for r in server.routes[0].routes if getattr(r, "path", None) == "/api/v1/health"]` has length 1.
  - Also append `test_health_route_reachable_through_start_server`: `client = TestClient(app_module.start_server())` (no `with` block, so the lifespan does not start), then assert `client.get("/api/v1/health")` has status 200 and `.json() == {"status": "ok"}`. This proves the route is not shadowed by `Mount("/")` (spec edge case "Route ordering", SC-002). Add `from starlette.testclient import TestClient` in ruff `I` order.
  - Leave the existing tests unchanged (makes T010 pass; FR-008).
- [X] T015 [US3] In `src/scaffold_ca_python/factory/entry_points/ep_mcp.py`, right after the `test_tools.py` `add_file`, add `builder.add_file(test_dir / "test_routes.py", builder.render(f"{base}/test_routes.py.jinja2", ctx_dict), template_name=f"{base}/test_routes.py.jinja2", is_test=True)`. Add `- tests/infrastructure/entry_points/mcp_server/test_routes.py` to the "Always queues" docstring list (makes T011 pass)
- [X] T016 [US3] Add `"src/tests/infrastructure/entry_points/mcp_server/test_routes.py"` to the `"gep:mcp"` list in `tests/factory/fixtures/dry_run_baseline.json` (after `test_app.py`, before `test_tools.py`). Then run `uv run pytest tests/factory/test_dry_run_parity.py` and confirm it passes (FR-011)
- [X] T017 [US3] Run T012 (`uv run pytest tests/commands/test_generate_entry_point.py -k health_route`) and confirm the generated `test_routes.py` and `test_app.py` pass and `ruff` is clean (SC-003)

**Checkpoint**: All three stories are complete. Generated MCP projects ship a working, tested, lint-clean health route.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 Confirm `--add-tool` leaves `routes.py` and `app.py` untouched: run `uv run pytest tests/commands/test_generate_entry_point.py -k add_tool`. `test_add_tool_only_modifies_tools_and_tests` snapshots every file, so it now also covers `routes.py` (spec edge case `gep --type mcp --add-tool`)
- [X] T019 Run the full gate: `uv run pytest` (coverage ≥ 80%), `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src` (SC-004)
- [X] T020 Walk through `specs/027-mcp-health-check/quickstart.md` sections 2–5 manually in `/tmp` (dry-run preview, generate + `ruff` + `pytest`, `curl` GET → 200 `{"status":"ok"}`, `curl -X POST` → 405, `--with-resources --with-prompts` regression)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: no dependencies.
- **US1 (T002–T006)**: after T001.
- **US2 (T007–T008)**: after T004. `app.py` imports `routes`, so the template must exist for an end-to-end run. The rendering tests themselves only need T001.
- **US3 (T009–T017)**:
  - T009–T011 can start after T001.
  - T012/T017 (end-to-end) need T005 and T008.
  - T015 edits the same file as T005, so it runs after T005.
  - T016 edits the same fixture as T006, so it runs after T006.
- **Polish (T018–T020)**: after all stories.

### Same-file Sequencing (no [P] between these)

- `tests/templates/test_entry_point_templates.py`: T002, T007, T009, T010 touch different sections. They can be authored in parallel by one person but must be merged carefully. Only T002/T009/T010 are marked [P] relative to tasks in *other* files.
- `src/scaffold_ca_python/factory/entry_points/ep_mcp.py`: T005 → T015
- `tests/factory/fixtures/dry_run_baseline.json`: T006 → T016
- `tests/factory/entry_points/test_ep_mcp.py`: T003 → T011

### Within Each User Story

Tests first (must fail) → template → factory → fixture → verify.

---

## Parallel Example: User Story 1

```bash
# Write the failing tests together (different files):
Task: "T002 routes.py.jinja2 rendering tests in tests/templates/test_entry_point_templates.py"
Task: "T003 routes.py queued test in tests/factory/entry_points/test_ep_mcp.py"
```

## Parallel Example: User Story 3

```bash
# Different files, all independent of US3 implementation:
Task: "T009/T010 test_routes + test_app rendering tests in tests/templates/test_entry_point_templates.py"
Task: "T011 test_routes.py queued test in tests/factory/entry_points/test_ep_mcp.py"
```

---

## Implementation Strategy

### MVP (US1 + US2 together)

US1 alone produces `routes.py`, but the endpoint only becomes reachable once US2 wires it. Treat T001–T008 as the MVP and validate with quickstart §4 (`curl`).

### Incremental Delivery

1. T001 → green baseline.
2. US1 (T002–T006) → `routes.py` generated and visible in the dry run.
3. US2 (T007–T008) → health endpoint live in generated servers.
4. US3 (T009–T017) → generated test scaffold plus end-to-end proof that it passes and is lint-clean.
5. Polish (T018–T020) → full gate and manual quickstart.

---

## Notes

- Do not modify `tools.py.jinja2`, `test_tools.py.jinja2`, the `--add-tool` code path, dependencies in `ep_mcp.py`, or `book_smcp/`.
- Do not edit `CHANGELOG.md` (release-please generates it). Use a conventional commit such as `feat(mcp): generate health check route for mcp entry point`.
- Do not commit without asking the user first.
