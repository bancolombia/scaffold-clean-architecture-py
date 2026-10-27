# Research: MCP Entry Point Health Check Route

**Feature**: `027-mcp-health-check` | **Date**: 2026-10-26

No `NEEDS CLARIFICATION` items remained after `/speckit-clarify`. The research below records the technical decisions that the plan depends on.

## R1 — How `FastMCP.custom_route` registers routes

- **Decision**: Use `@mcp.custom_route(name="health_check", path="/api/v1/health", methods=["GET"])` inside `bind_routes(mcp)`.
- **Rationale**: Verified in the installed SDK (`mcp/server/fastmcp/server.py`): `custom_route(path, methods, name=None, include_in_schema=True)` appends a Starlette `Route` to `self._custom_starlette_routes`, and `streamable_http_app()` copies that list into the Starlette app it builds (`routes.extend(self._custom_starlette_routes)`), after the `/mcp` route (lowest matching precedence). No new dependency is needed.
- **Alternatives considered**: Adding a separate Starlette `Route` next to the `Mount("/")` in `start_server()` — rejected because it moves route wiring into the composition root and bypasses the `bind_*` pattern already used by `tools`, `resources`, and `prompts`.

## R2 — When to call `bind_routes(mcp)`

- **Decision**: Call `routes.bind_routes(mcp)` once at module level in `app.py`, immediately after `mcp: FastMCP = FastMCP(...)` (clarification Q2).
- **Rationale**:
  - `streamable_http_app()` takes a snapshot of the custom routes when `start_server()` runs. Tools, resources, and prompts are bound later, inside `lifespan`, so binding the health route there would leave it out of the route table.
  - `custom_route` does not deduplicate. A module-level call happens once per process, so repeated `start_server()` calls in `test_app.py` do not accumulate duplicate routes.
- **Alternatives considered**: Inside `start_server()` (works in production, duplicates routes in tests); inside `lifespan` (route never registered).

## R3 — `bind_routes` is synchronous

- **Decision**: `def bind_routes(mcp: FastMCP) -> None` (not `async`), without `@inject`.
- **Rationale**: It runs at import time, outside an event loop, and has no dependencies to inject. Only the handler `health_check` is `async`, which satisfies Principle IV (async I/O in generated code).
- **Alternatives considered**: `async def bind_routes` awaited from `lifespan` for symmetry with `bind_tools` — rejected by R2.

## R4 — Lint compliance of the generated `routes.py`

- **Decision**: Render the reference code with minimal fixes: module docstring, `from __future__ import annotations`, sorted imports (`JSONResponse, Response`), two blank lines before `def`, and `-> None` on `bind_routes` (clarification Q1).
- **Rationale**: Generated projects run `ruff` with `select = ["E", "F", "I", "UP", "ANN"]`. The raw reference fails `I001` (unsorted imports) and `ANN201` (missing return type). `from __future__ import annotations` is safe here because neither `custom_route` nor Starlette's `Route` inspects handler annotations.
- **Alternatives considered**: `noqa` comments or per-file ignores — rejected; they add noise to generated code.

## R5 — How the generated tests exercise the route

- **Decision**: `test_routes.py` builds a fresh `FastMCP("test")`, calls `bind_routes(mcp)`, wraps `mcp.streamable_http_app()` in `starlette.testclient.TestClient` (used **without** a `with` block, so the MCP session-manager lifespan is not started), and asserts:
  - `GET /api/v1/health` returns 200 with body `{"status": "ok"}`.
  - `POST /api/v1/health` returns 405.
- **Rationale**:
  - `TestClient` needs `httpx`, which `mcp` already declares (`Requires-Dist: httpx>=0.27.1`). The generated pyproject already filters httpx deprecation warnings, so no new test dependency is needed.
  - A fresh `FastMCP` per test avoids touching the module-level instance in `app.py`.
  - Starlette answers 405 when the path matches but the method does not. It also adds `HEAD` automatically for `GET` routes.
- **Alternatives considered**: Building a bare `Starlette(routes=mcp._custom_starlette_routes)` — rejected because it relies on a private attribute.

## R6 — How `test_app.py` asserts single registration

- **Decision**: Call `start_server()` twice, then assert that `/api/v1/health` appears exactly once among the routes of the mounted app (`server.routes[0].routes`, i.e. `Mount.routes`, which proxies to the inner Starlette app).
- **Rationale**: Locks in FR-008 and the clarification Q2 guarantee using only public Starlette APIs.

## R7 — CLI-side test and fixture impact

- **Decision**:
  - Add `routes.py` and `test_routes.py` to the `gep:mcp` entry in `tests/factory/fixtures/dry_run_baseline.json`.
  - Add a factory test in `tests/factory/entry_points/test_ep_mcp.py`.
  - Add template rendering tests in `tests/templates/test_entry_point_templates.py`, covering the new templates plus the `app.py`/`test_app.py` changes.
- **Rationale**:
  - The dry-run parity test compares sorted queued paths against the baseline.
  - Principle II requires rendering tests per template group, and `entry_point/mcp/` is already covered in that file.
- **Alternatives considered**: None.

## R8 — SDK version drift

- **Decision**: Keep the `mcp~=1.30.0` pin; no change.
- **Rationale**: `custom_route` and `streamable_http_app` exist with the same signatures in the 1.x line (verified against an installed 1.27.0; the 1.30 pin targets the same FastMCP API, as noted in `ep_mcp.py`).
