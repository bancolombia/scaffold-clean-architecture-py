# Contract: Generated File Layout per Command

**Feature**: 028-wireup-di

All paths are relative to `src/<python_package>/` unless otherwise noted.

---

## `scaffold ca --name <name>` (generate-project)

**New files** (wireup project):

```
application/config/__init__.py
application/config/config.py               # Settings: ENV, LOG_LEVEL only
application/config/wiring.py               # INJECTABLES + create_container()
application/config/usecases/__init__.py    # empty, scanned by wireup
src/tests/application/config/test_config.py    # NEW (FR-033)
src/tests/application/config/test_wiring.py    # NEW (FR-033, FR-034)
src/tests/test_main.py                          # NEW (FR-033)
```

**NOT generated** (compared to 0.5.0):
- `application/config/container.py`
- `application/config/resource_container.py`
- `application/config/driven_adapters_container.py`
- `application/config/usecases_container.py`

**pyproject.toml changes** vs 0.5.0:
- `dependency-injector==4.49.1` → `wireup==2.13.0`
- `[tool.scaffold-ca-python]` gains `scaffold_version = "<installed version>"`
- ruff: `extend-select = ["ASYNC"]`; `extend-ignore = ["TC"]`
- pytest: `asyncio_mode = "auto"`
- dev group: `mypy==<pin>` added

---

## `scaffold guc --name <name> [--uses <gw1>[,<gw2>]]` (generate-use-case)

**Always generated**:
```
domain/usecase/<name>_usecase.py
tests/.../test_<name>_usecase.py
```

**Generated when `--uses` is provided** (additional):
```
application/config/usecases/<name>_usecase.py               # @injectable factory
src/tests/application/config/usecases/test_<name>_usecase.py  # factory test (FR-036)
```

**Appended when `--uses` is provided**:
- `src/tests/application/config/test_wiring.py` ← `test_container_resolves_<name>_usecase` (idempotent, FR-034); `MISSING_ADAPTERS` updated (FR-037)

**Hint printed** when no driven adapter with `as_type=<Gw>` found (FR-035):
```
Next step: scaffold gda --type <type> --name <adapter> --gateway <gw>
```

**Deleted by `scaffold dm --name <name>`**:
```
domain/usecase/<name>_usecase.py
tests/.../test_<name>_usecase.py
application/config/usecases/<name>_usecase.py                  # if it exists
src/tests/application/config/usecases/test_<name>_usecase.py   # if it exists
```

**Also modified by `scaffold dm`**:
- `src/tests/application/config/test_wiring.py` ← removes `test_container_resolves_<name>_usecase` and `test_container_resolves_<name>` (FR-034); `MISSING_ADAPTERS` re-synced (FR-037)

---

## `scaffold gda --type generic --name <name> [--gateway <gw>]`

```
infrastructure/driven_adapters/<name>/<name>_adapter.py    # @injectable [(as_type=<Gw>)]
infrastructure/driven_adapters/<name>/__init__.py
tests/.../test_<name>_adapter.py
```

**When `--gateway <gw>` is provided**:
- Adapter class inherits from `<Gw>` and carries `@wireup.injectable(as_type=<Gw>)`.
- Gateway ABC is imported from `domain/model/*/gateways/<gw>.py`.
- `src/tests/application/config/test_wiring.py` ← `async def test_container_resolves_<name>` appended (idempotent, FR-034); it awaits `container.get(<Gw>)`. `MISSING_ADAPTERS` re-synced (FR-037).

No additional files (generic adapter; resource convention is documented, not generated).

---

## `scaffold gda --type rest-consumer --name <name>`

```
infrastructure/driven_adapters/rest_consumer/rest_consumer.py           # @injectable(as_type=<Gw> if provided)
infrastructure/driven_adapters/rest_consumer/rest_consumer_settings.py   # RestConsumerSettings(BaseSettings)
infrastructure/driven_adapters/rest_consumer/rest_consumer_config.py     # async yield: httpx.AsyncClient
infrastructure/driven_adapters/rest_consumer/__init__.py
tests/.../rest_consumer/test_rest_consumer.py
src/tests/conftest.py                                       # autouse fixture REST_CONSUMER_BASE_URL (appended idempotently, FR-039)
```

Dependencies added to `pyproject.toml`: `httpx~=<version>`; `respx` in test group.

**`src/tests/conftest.py`**: Created by `ca` (empty stub) or appended to by `gda rest-consumer`. Contains an autouse pytest fixture that sets `REST_CONSUMER_BASE_URL` in the test environment, ensuring wiring tests can resolve the container even when the adapter is registered (D5: required env var). The fixture is idempotent — running `gda rest-consumer` multiple times does not duplicate it.

---

## `scaffold gda --type secrets --name <name>`

```
infrastructure/driven_adapters/<name>/<name>_adapter.py    # @injectable
infrastructure/driven_adapters/<name>/<name>_settings.py   # SecretsSettings(BaseSettings)
infrastructure/driven_adapters/<name>/__init__.py
tests/.../test_<name>_adapter.py
```

Dependency added: `boto3~=<version>`.

---

## `scaffold gh --name <name>` (generate-helper)

```
infrastructure/helpers/<name>/<name>.py    # @injectable, infra-only docstring
infrastructure/helpers/<name>/__init__.py
tests/.../test_<name>.py
```

---

## `scaffold gep --type restapi`

```
infrastructure/entry_points/api/v1/rest_controller.py   # Injected[...] example
application/app.py                                       # wireup.integration.fastapi.setup + lifespan
application/server.py
tests/.../test_rest_controller.py                        # override.injectable example
```

---

## `scaffold gep --type mcp`

```
infrastructure/entry_points/mcp_server/tools.py     # Injected[...], inject_from_container
infrastructure/entry_points/mcp_server/prompts.py   # Injected[...]
infrastructure/entry_points/mcp_server/resources.py # Injected[...]
application/mcp_app.py                               # async contextmanager + inject_from_container
application/mcp_server.py
tests/.../test_tools.py
tests/.../test_resources.py
```

---

## `scaffold gep --type agent`

A2A server (US4, FR-040–FR-048). Paths are relative to `src/<pkg>/` unless they start with `src/tests/`.

```
server.py                                              # NEW — main(): uvicorn.run(start_server(), host, port)
main.py                                                # DELETED
application/app.py                                     # Starlette + lifespan (mounts A2A routes once) + create_a2a_container()
application/config/config.py                           # MODIFIED — HOST / PORT inserted after LOG_LEVEL
infrastructure/entry_points/a2a_server/__init__.py
infrastructure/entry_points/a2a_server/agent_settings.py   # AgentSettings(env_prefix="AGENT_") + @wireup.injectable factory
infrastructure/entry_points/a2a_server/a2a_config.py       # @wireup.injectable: TaskStore, AgentCard, AgentExecutor, RequestHandler
infrastructure/entry_points/a2a_server/agent_executor.py   # A2AExecutor hello world + commented use-case hook
infrastructure/entry_points/a2a_server/agent_card.py       # build_agent_card(settings) -> AgentCard (skill "hello_world")
infrastructure/entry_points/a2a_server/routes.py           # GET /api/v1/health
src/tests/application/test_app.py                          # health, agent card, JSON-RPC SendMessage, container resolution
src/tests/infrastructure/entry_points/a2a_server/test_agent_executor.py
src/tests/infrastructure/entry_points/a2a_server/test_agent_card.py
src/tests/infrastructure/entry_points/a2a_server/test_routes.py
```

**`pyproject.toml`**:
- Dependencies added: `a2a-sdk[http-server]~=1.1.4`, `starlette~=1.6.0`, `uvicorn[standard]~=0.53.0`, `wireup~=2.13.0`, `pydantic-settings~=2.15.0` (skipped when already present by name).
- `[project.scripts]`: `<script> = "<pkg>.server:main"`.

**Not modified**: `application/config/wiring.py` (the A2A factories are added by `create_a2a_container()` in `app.py`).

**Conflicts**: refused (exit 1, nothing written) when a `restapi` (`entry_points/api/`) or `mcp` (`entry_points/mcp_server/`) entry point exists; `restapi` and `mcp` are refused when `entry_points/a2a_server/` exists.

**Removed flags**: `--enable-kafka`, `--enable-mcp-client` (Typer exits 2).

**Runtime contract** (zero configuration):

| Route | Method | Result |
|-------|--------|--------|
| `/api/v1/health` | GET | `200 {"status": "ok"}` |
| `/.well-known/agent-card.json` | GET | Agent card: `name` from `AGENT_NAME` (default: project name), interfaces `JSONRPC` (`<public_url>/`) and `HTTP+JSON` (`<public_url>`), skill `hello_world` |
| `/` | POST (JSON-RPC `SendMessage`) | Completed task with artifact `Hello, World! You said: <text>` |
| `/message:send` | POST (REST `SendMessage`) | Same result as JSON-RPC; other REST routes come from `create_rest_routes` |

Requests to `/` and the REST routes MUST carry the header `A2A-Version: 1.0`; without it a2a-sdk 1.1 answers with a version error.

Environment variables: `HOST` (default `0.0.0.0`), `PORT` (default `8000`), `AGENT_NAME`, `AGENT_DESCRIPTION`, `AGENT_VERSION`, `AGENT_PUBLIC_URL` (default `http://localhost:8000`).

---

## `scaffold gep --type generic`

```
infrastructure/entry_points/generic/entry_point.py
application/generic_app.py                           # async with create_generic()
main.py                                              # asyncio.run + existing function import
tests/.../test_entry_point.py
```

---

---

## Legacy Projects (FR-020)

All `generate-*` commands that modify an existing project (`gm`, `guc`, `gda`, `gh`, `gep`, `--add-tool`, `gp`, `dm`, `up`) MUST refuse (exit 1) when the project's `[tool.scaffold-ca-python]` section lacks the `scaffold_version` key. The error message MUST point to [docs/spec-029-migrate-di](../../../docs/spec-029-migrate-di/README.md) and MAY name the planned `scaffold migrate-di` / `--install-skill` commands.

No files are written. `ca` (creates a new project) and `vs` (read-only) are exempt.

---

## Migration (`scaffold migrate-di`)

**Out of scope for spec 028.** File layout, flags, and report schema: [docs/spec-029-migrate-di/contracts/migrate-di.md](../../../docs/spec-029-migrate-di/contracts/migrate-di.md).
