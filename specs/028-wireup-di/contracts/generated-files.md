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
infrastructure/driven_adapters/<name>/<name>_adapter.py    # @injectable(as_type=<Gw> if provided)
infrastructure/driven_adapters/<name>/<name>_settings.py   # RestConsumerSettings(BaseSettings)
infrastructure/driven_adapters/<name>/<name>_config.py     # async yield: httpx.AsyncClient
infrastructure/driven_adapters/<name>/__init__.py
tests/.../test_<name>_adapter.py
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

```
infrastructure/entry_points/agent/agent.py   # <PascalName>Agent class (no hyphens)
application/agent_app.py                     # async with create_agent(); container.close()
main.py                                      # asyncio.run + existing function import
tests/.../test_agent.py
```

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

All `generate-*` commands that modify an existing project (`gm`, `guc`, `gda`, `gh`, `gep`, `--add-tool`, `gp`, `dm`, `up`) MUST refuse (exit 1) when the project's `[tool.scaffold-ca-python]` section lacks the `scaffold_version` key. The error message MUST include both:
- `scaffold migrate-di` (automated codemod)
- `scaffold migrate-di --install-skill` (agent-assisted migration)

No files are written. `ca` (creates a new project) and `vs` (read-only) are exempt.

---

## `scaffold migrate-di [--dry-run] [--yes] [--report json] [--install-skill] [--target <t>] [--force]`

**Files written by `--yes`** (not written by `--dry-run`):

```
pyproject.toml                                          # updated in-place
application/config/wiring.py                           # NEW
application/config/usecases/<name>_usecase.py          # one per use case found in containers
application/config/usecases/__init__.py                # NEW
infrastructure/driven_adapters/**/<name>_adapter.py    # @injectable added
infrastructure/helpers/**/<name>.py                    # @injectable added
infrastructure/entry_points/**/*.py                    # Provide → Injected, @inject removed
```

**Files deleted by `--yes`**:
```
application/config/container.py
application/config/resource_container.py
application/config/driven_adapters_container.py
application/config/usecases_container.py
```

**Files installed by `--install-skill`** (in the target project, not the scaffolder repo):
```
.claude/skills/migrate-di/SKILL.md
.claude/skills/migrate-di/references/recipes.md
.claude/skills/migrate-di/references/errors.md
.claude/skills/migrate-di/references/checklist.md
.cursor/skills/migrate-di/SKILL.md
.cursor/skills/migrate-di/references/...
.agents/skills/migrate-di/SKILL.md
.agents/skills/migrate-di/references/...
AGENTS.md                                               # line appended (created if absent)
```
