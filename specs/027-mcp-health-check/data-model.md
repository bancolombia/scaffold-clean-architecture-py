# Data Model: MCP Entry Point Health Check Route

**Feature**: `027-mcp-health-check`

This feature adds no domain models, Pydantic context models, or persisted data. The only "data" is the generated HTTP contract and the files queued by the factory.

## Health Response (generated project)

| Field | Type | Value | Rule |
|---|---|---|---|
| `status` | string | `"ok"` | Always `"ok"` when the process serves HTTP; no other fields. |

- Served at `GET /api/v1/health` (also `HEAD`, added automatically by Starlette).
- Content type `application/json`, HTTP 200.
- Any other method returns HTTP 405.
- It is a stateless liveness signal: it does not depend on the DI container, the domain, or driven adapters.

## Template Context (CLI)

`routes.py.jinja2` and `test_routes.py.jinja2` reuse the existing module context (`builder.module_ctx.model_dump()`, i.e. `project.python_package`, `project.name`) already passed to the other `entry_point/mcp/` templates. No new context fields or Pydantic models are introduced (Principle II is unaffected).

## Files Queued by `EntryPointMcp.build()`

| Path | Template | Condition | Change |
|---|---|---|---|
| `src/<pkg>/infrastructure/entry_points/mcp_server/routes.py` | `entry_point/mcp/routes.py.jinja2` | always | **NEW** |
| `<tests_root>/infrastructure/entry_points/mcp_server/test_routes.py` | `entry_point/mcp/test_routes.py.jinja2` (`is_test=True`) | always | **NEW** |
| `src/<pkg>/application/app.py` | `entry_point/mcp/app.py.jinja2` | always | MODIFIED: import `routes`; `routes.bind_routes(mcp)` after `mcp` creation |
| `<tests_root>/infrastructure/entry_points/mcp_server/test_app.py` | `entry_point/mcp/test_app.py.jinja2` | always | MODIFIED: asserts health route registered exactly once and reachable through `start_server()` |

All other queued files, dependencies, and overwrite flags are unchanged. The new files use the default `overwrite=False`, the same as `tools.py`.
