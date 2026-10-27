# Contract: Generated MCP Health Route

**Feature**: `027-mcp-health-check`

The CLI's public interface (`gep --type mcp` and its flags) does not change. The contract below describes the **generated output**, which is what consumers depend on.

## 1. HTTP contract (generated server)

| Request | Status | Body |
|---|---|---|
| `GET /api/v1/health` | `200` | `{"status": "ok"}` (`application/json`) |
| `HEAD /api/v1/health` | `200` | empty |
| `POST`/`PUT`/`DELETE`/`PATCH /api/v1/health` | `405` | Starlette default |

- No authentication.
- Served on the same `HOST`/`PORT` as the MCP endpoint (`/mcp`).

## 2. Generated `routes.py`

Path: `src/<pkg>/infrastructure/entry_points/mcp_server/routes.py`

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

The file must pass the generated project's `ruff check` (`E`, `F`, `I`, `UP`, `ANN`).

## 3. Generated `app.py` delta

```python
from {{ project.python_package }}.infrastructure.entry_points.mcp_server import routes, tools
# ... optional resources / prompts imports unchanged ...

mcp: FastMCP = FastMCP("{{ project.name }}", stateless_http=True)
routes.bind_routes(mcp)
```

- `lifespan` is unchanged. `routes` is **not** added to `container.wire(...)`.
- `start_server()` is unchanged and MUST NOT call `bind_routes`.

## 4. Generated tests

- **`test_routes.py`** (new):
  - `bind_routes(FastMCP("test"))` registers `/api/v1/health`.
  - `GET` returns 200 with `{"status": "ok"}`.
  - `POST` returns 405.
  - Uses `starlette.testclient.TestClient` without starting the lifespan.
- **`test_app.py`** (modified):
  - After calling `start_server()` twice, `/api/v1/health` appears exactly once in the mounted app's routes.
  - `TestClient(start_server()).get("/api/v1/health")` returns 200 with `{"status": "ok"}`, without starting the lifespan.

## 5. CLI dry-run contract

`gep --type mcp --dry-run` lists, in addition to the current files:

```text
src/<pkg>/infrastructure/entry_points/mcp_server/routes.py
<tests_root>/infrastructure/entry_points/mcp_server/test_routes.py
```
