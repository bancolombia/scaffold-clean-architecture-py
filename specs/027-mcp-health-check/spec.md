# Feature Specification: MCP Entry Point Health Check Route

**Feature Branch**: `feature/mcp-health-check`

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "When the `mcp` entry point is generated, also generate a health endpoint in a module named `routes.py` inside `infrastructure/entry_points/mcp_server/`, exposing a `GET /api/v1/health` health check that returns `{\"status\": \"ok\"}` via a `bind_routes(mcp)` function."

## Clarifications

### Session 2026-10-26

- Q: Should the generated `routes.py` follow the reference code exactly, or be adjusted so it passes the generated project's lint rules? → A: Keep the reference behavior and structure, with minimal lint fixes (`-> None` on `bind_routes`, sorted imports, module docstring, `from __future__ import annotations`, matching `tools.py`).
- Q: Where in the generated `app.py` should `routes.bind_routes(mcp)` be called: once at module level right after `mcp` is created, or inside `start_server()`? → A: At module level, immediately after `mcp` is created; registered exactly once per process.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Generated MCP server exposes a health check out of the box (Priority: P1)

A developer generates an MCP entry point (`scaffold-ca-python gep --type mcp`) in a Clean Architecture project. Without writing any extra code, the resulting server answers a health check request so it can be deployed behind load balancers, container orchestrators (liveness/readiness probes), and uptime monitors.

**Why this priority**: A health endpoint is a baseline operational requirement for any deployable service. Without it, every team must hand-write the same route before the server can run in a managed environment.

**Independent Test**: Run `gep --type mcp --dry-run` and confirm `routes.py` is listed; render `routes.py` and confirm `bind_routes` registers `GET /api/v1/health` returning `{"status": "ok"}` on a standalone `FastMCP` instance. (Reaching the endpoint on the running server additionally requires User Story 2.)

**Acceptance Scenarios**:

1. **Given** a freshly scaffolded project, **When** the developer runs `gep --type mcp`, **Then** a `routes.py` module is created at `src/<pkg>/infrastructure/entry_points/mcp_server/routes.py` alongside `tools.py`.
2. **Given** the generated `routes.py`, **When** the developer inspects it, **Then** it exposes a single public function `bind_routes(mcp)` that registers a route named `health_check` at path `/api/v1/health` registered for `GET`.
3. **Given** the generated MCP server is running, **When** a client sends `GET /api/v1/health`, **Then** the server responds with HTTP 200, a JSON content type, and the body `{"status": "ok"}`.
4. **Given** the generated MCP server is running, **When** a client sends any method other than `GET` or `HEAD` (e.g. `POST`) to `/api/v1/health`, **Then** the server rejects it with HTTP 405.

---

### User Story 2 - Health route is wired into the composition root automatically (Priority: P1)

The developer does not have to edit the application composition root to activate the health route; the generated `app.py` already binds it so the endpoint is live as soon as the server starts.

**Why this priority**: A generated route that is not wired is dead code. Wiring is part of the same deliverable as Story 1 and is required for its acceptance scenario 3 to pass.

**Independent Test**: Render the generated `app.py`, build the ASGI application with `start_server()`, and confirm the `/api/v1/health` route is present in the application's route table before any request or lifespan event runs.

**Acceptance Scenarios**:

1. **Given** the generated `application/app.py`, **When** the developer inspects it, **Then** it imports `routes` from the `mcp_server` package and calls `routes.bind_routes(mcp)`.
2. **Given** the generated application, **When** `start_server()` builds the ASGI app, **Then** the health route is already registered (it is bound at module import time, not inside `start_server()` or the lifespan).
3. **Given** the generated application, **When** `start_server()` is called multiple times in the same process (e.g. across tests), **Then** `/api/v1/health` appears exactly once in the route table.
4. **Given** the generated application with resources and/or prompts enabled, **When** the server starts, **Then** the health route is still registered and the existing tools/resources/prompts behaviour is unchanged.

---

### User Story 3 - Generated project ships a test for the health route (Priority: P2)

The generated project includes a test file for `routes.py` so the health contract is covered from day one and TDD remains the default workflow.

**Why this priority**: Required by the constitution (Principle V: every `generate-*` command MUST produce a corresponding test scaffold), but the server is still operable without it.

**Independent Test**: Generate a project with the `mcp` entry point and run its test suite; the routes test passes without modification.

**Acceptance Scenarios**:

1. **Given** `gep --type mcp` was run, **When** the developer lists the tests, **Then** `tests/infrastructure/entry_points/mcp_server/test_routes.py` exists (resolved through the project's tests root).
2. **Given** the generated test, **When** it runs, **Then** it asserts that `GET /api/v1/health` returns 200 with body `{"status": "ok"}`.

---

### Edge Cases

- **Dry run**: `gep --type mcp --dry-run` MUST list `routes.py` and `test_routes.py` in the preview and write nothing to disk.
- **Existing MCP entry point**: If `mcp_server/` already exists, `gep --type mcp` aborts with the existing "Directory already exists" error before writing `routes.py` (no new policy is introduced).
- **Conflicting entry point**: When the `restapi` entry point is already present, the existing MCP/restapi conflict check still aborts generation before `routes.py` is written.
- **Optional primitives**: The health route is generated regardless of `--with-resources` / `--with-prompts`; it is not gated by any flag.
- **`gep --type mcp --add-tool`**: Adding tools afterwards MUST NOT modify or remove `routes.py` or its binding in `app.py`.
- **Route ordering**: The health route MUST NOT be shadowed by the MCP HTTP app mounted at `/`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `mcp` entry-point generator MUST always emit `src/<pkg>/infrastructure/entry_points/mcp_server/routes.py`, independent of optional flags.
- **FR-002**: `routes.py` MUST be rendered from a new Jinja2 template under the existing `entry_point/mcp/` template group (no string assembly), per Principle II.
- **FR-003**: `routes.py` MUST expose a synchronous public function `bind_routes(mcp)` that receives the server's `FastMCP` instance and registers the health route on it.
- **FR-004**: The health route MUST be named `health_check`, served at `/api/v1/health`, accept `GET` (Starlette implicitly also answers `HEAD` for `GET` routes), and be implemented as an `async` handler (Principle IV: async-first in generated code).
- **FR-005**: The health route MUST respond with HTTP 200 and the JSON body `{"status": "ok"}`, with no dependency on the DI container, domain, or driven adapters.
- **FR-006**: The generated `application/app.py` MUST import `routes` and call `routes.bind_routes(mcp)` once at module level, immediately after the `mcp` instance is created, so the route is registered exactly once per process and before `start_server()` builds the ASGI application. `start_server()` MUST NOT register routes, and `routes` is not added to `container.wire(...)`.
- **FR-007**: The generator MUST emit `tests/infrastructure/entry_points/mcp_server/test_routes.py` (via the resolved tests root) covering the 200/`{"status": "ok"}` contract and the 405 response for `POST`.
- **FR-008**: The generated `test_app.py` MUST assert that the `/api/v1/health` route is present exactly once in the application returned by `start_server()`, and that `GET /api/v1/health` against that application returns 200 with `{"status": "ok"}`.
- **FR-009**: The generated `routes.py` and `test_routes.py` MUST pass the generated project's `ruff` lint configuration.
- **FR-010**: The generated `routes.py` MUST only import from the MCP SDK and Starlette (already declared dependencies); no new runtime dependency is added.
- **FR-011**: `--dry-run` output for `gep --type mcp` MUST include both new files, and the dry-run parity baseline MUST be updated accordingly.
- **FR-012**: The CLI test suite MUST include template rendering tests for `routes.py.jinja2` and `test_routes.py.jinja2` under `tests/templates/`, plus factory tests asserting the files are queued by the `mcp` entry-point factory.
- **FR-013**: The generated `routes.py` MUST keep the behavior and structure of the requester's reference code, adjusted only as needed to satisfy FR-009 (`ruff` rules `E`, `F`, `I`, `UP`, `ANN`) and to match the conventions of `tools.py`. Expected output:

  ```python
  """MCP custom routes binding — register non-MCP HTTP routes such as the health check."""

  from __future__ import annotations

  from mcp.server.fastmcp import FastMCP
  from starlette.requests import Request
  from starlette.responses import JSONResponse, Response


  def bind_routes(mcp: FastMCP) -> None:
      """
      Bind routes to the FastMCP instance.
      """

      @mcp.custom_route(name="health_check", path="/api/v1/health", methods=["GET"])
      async def health_check(_request: Request) -> Response:
          """
          Health check endpoint to verify the server is running.

          Returns:
              JSON response indicating the server is healthy.
          """

          response_data = {"status": "ok"}
          return JSONResponse(response_data)
  ```

### Key Entities

- **Health response**: A minimal payload with a single field `status` whose value is `"ok"` when the server process is up and able to serve HTTP requests.
- **Route binder (`bind_routes`)**: The single extension point for non-MCP HTTP routes of the generated server; future custom routes are added inside it.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of projects generated with `gep --type mcp` contain `routes.py` and `test_routes.py`, verified by the CLI factory tests.
- **SC-002**: A freshly generated MCP project answers `GET /api/v1/health` with `{"status": "ok"}` with zero manual edits by the developer.
- **SC-003**: The generated project's test suite passes on first run, including the new routes test.
- **SC-004**: The CLI test suite keeps its ≥ 80% coverage gate and all existing MCP entry-point tests still pass unchanged (other than the intended dry-run baseline update).

## Assumptions

- The health check is a **liveness** signal only: it reports that the process is serving HTTP and does not probe downstream dependencies (databases, external APIs). Readiness checks are out of scope.
- The health route is public (no authentication), consistent with standard probe usage.
- The path `/api/v1/health` is fixed; making it configurable via settings is out of scope.
- The health route is served by the same host/port as the MCP server (existing `HOST`/`PORT` settings); no separate listener is introduced.
- Only the `mcp` entry point is affected; `restapi`, `agent`, and `generic` entry points are unchanged.
- Existing projects that already generated the MCP entry point are not migrated. Re-running `gep --type mcp` is blocked by the existing `mcp_server/` directory guard, so those projects must add `routes.py` and the `routes.bind_routes(mcp)` line in `app.py` manually.
- Only `ruff` compliance is required for generated files; `mypy --strict` compliance of the generated project is out of scope (`FastMCP.custom_route` is an untyped decorator).
- The reference `book_smcp/` sample project is not part of this feature's scope.
