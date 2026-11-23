# Research: Wireup DI Migration

**Feature**: 028-wireup-di | **Date**: 2026-10-29

This document records the research and spike findings that informed the design decisions in `plan.md`. All decisions were validated in the spike on branch `feature/di-alternatives-spike` (not present on `main`; consulted with `git show`).

---

## Decision 1: DI library choice

**Decision**: wireup 2.13.0

**Rationale**:
- Validates the dependency graph at container creation; `dependency-injector` only fails at first resolution.
- Async-native: `create_async_container` supports async factories (`yield`) for resource lifecycle natively.
- Typed injection: `Injected[T]` is checked by mypy; `Provide["name"]` is not.
- Domain stays decorator-free (Variant B): only adapters, helpers, and factories carry wireup decorators.
- Smallest DI footprint in generated projects: one `wiring.py` + one file per use case.

**Alternatives considered**:
- `dependency-injector` (opt1/opt2): retained for legacy support only. Opt1 requires marker-based codegen; opt2 cannot handle resources, third-party types, or primitive config parameters.
- `wireup` Variant A (single `wiring.py` with all factories): works, but adding a use case always edits `wiring.py` creating merge conflict risk.

**Maintenance risk**: wireup has fewer contributors than dependency-injector. Mitigated by the fact that the domain carries zero wireup imports, so the switching cost is bounded to `application/` and `infrastructure/` entry points.

---

## Decision 2: Factory placement — one file per use case

**Decision**: `application/config/usecases/<snake_name>.py`, scanned as a package

**Rationale**:
- `generate-use-case` creates a file; `delete-module` deletes it. No central file is ever edited by the scaffolder.
- Eliminates the `# scaffold:usecases` marker and `insert_after` logic.
- Merge conflicts on `wiring.py` are impossible when two developers add use cases in parallel.

**Validated in spike**: `wireup.create_async_container(injectables=[usecases_pkg, ...])` works with a real package on disk (not fake in-memory modules; wireup requires `__file__`).

**Alternatives considered**: marker in `wiring.py` (original RF-2) — functional but fragile under concurrent development.

---

## Decision 3: Adapter configuration — typed per-adapter Settings

**Decision**: `<Name>Settings(BaseSettings)` with `env_prefix`, injected by type; fields without defaults for required connection params

**Rationale**:
- pydantic-settings raises `ValidationError` at startup when a required env var is absent — before the wireup container is even built.
- mypy verifies the settings type end-to-end.
- Settings live in the adapter's own package (co-located), not in the central `config.py`. No file is edited when a new adapter is added.

**Validated in spike**: wireup 2.13.0 can register a `BaseSettings` subclass as `@injectable` and inject it by type.

**Alternatives considered**: `Inject(config="db_timeout")` with text keys — works but not type-safe; central `config.py` grows with every adapter.

---

## Decision 4: Codemod library — libcst

**Moved to [specs/029-upgrade-framework](../../specs/029-upgrade-framework/spec.md)** (implemented as the `scaffold up` upgrade action).

**Decision**: libcst for all source-to-source transformations in the `scaffold up` dependency-injector → wireup action

**Rationale**:
- Preserves comments, blank lines, and formatting that `ast`-based rewriting would destroy.
- Used by `bump-pydantic` (Pydantic v1→v2 migrator) for the same class of problem.
- Pattern-based: a `MatcherDecoratableTransformer` per transform kind keeps the code modular and testable in isolation.

**Alternatives considered**: `ast` + `astor` — loses comments; regex — too fragile for Python syntax.

**Risk**: libcst adds a runtime dependency to the scaffolder. Acceptable because `scaffold up` is a core command; libcst is imported only when the action runs. If this becomes a concern, it can be moved to an optional extra in a future release.

---

## Decision 5: Migration exit codes

**Moved to [specs/029-upgrade-framework](../../specs/029-upgrade-framework/spec.md)**.

**Decision**: 0 = no changes needed; 1 = applied, no pending; 2 = applied, pending items remain; 3 = precondition failure; 4 = post-verification failure

**Rationale**: The agent skill must decide the next action without parsing human-readable output. Distinct exit codes let `SKILL.md` branch on the result deterministically.

---

## Decision 6: Async-first for all entry points

**Decision**: Single `create_async_container`; all four entry-point types use it; no sync container generated

**Rationale**:
- wireup raises `WireupError: ... is an async dependency and it cannot be created in a synchronous context` if a sync container tries to resolve an async resource. Once any adapter has an async resource (pool, HTTP client), all sync entry points break.
- FastAPI, the MCP SDK, and modern HTTP/DB clients are async-native.
- CPython free-threading (3.14+) does not yet replace asyncio for I/O-heavy services.

**Validated in spike**: all four entry-point types (restapi, mcp, agent, generic) work correctly with the async container.

---

## Decision 7: Helpers are infrastructure-only (D7)

**Decision**: Helpers are `@injectable` and may be injected in driven adapters and entry points only. Use cases depend solely on domain gateway ABCs.

**Rationale**:
- A use case that depends on a helper imports from `infrastructure`, which violates Clean Architecture layers.
- `validate-structure` already flags this. `guc --uses` reinforces it by rejecting helper names with a clear hint.
- A use case that needs a technical capability (e.g., ID generation) models it as a domain gateway; the helper implements the gateway's driven adapter.

---

## Decision 8: Agent skill packaging — inside the wheel

**Moved to [specs/029-upgrade-framework](../../specs/029-upgrade-framework/spec.md)**.

**Decision**: `src/scaffold_ca_python/skills/migrate-di/` included in the wheel (shipped by the hatch `packages` setting)

**Rationale**:
- Skill version is always in sync with the scaffolder version (no separate install step).
- `importlib.resources` copies the skill to the target project; no filesystem path assumptions.
- The skill targets Claude Code (`.claude/skills/`), Cursor (`.cursor/skills/`), and the Agent Skills generic spec (`.agents/skills/`).

---

## Decision 9: A2A agent entry point (US4)

**Decision**: `gep agent` generates an open A2A server (a2a-sdk 1.1.x) on Starlette + uvicorn, with a hello-world `A2AExecutor` and commented use-case hooks. The base `wiring.py` scans `infrastructure/entry_points` (`INJECTABLES = [driven_adapters, entry_points, helpers, usecases]`), so the A2A factories register without editing it; `application/app.py` reuses `create_container()`. The A2A protocol routes are mounted once in the lifespan.

**Rationale**:
- **Open by default**: the entry point only translates the protocol (anti-corruption layer). No response model, gateway, LLM, LangGraph, persistence, or observability is imposed; those belong to the developer's domain and driven adapters. This follows the same philosophy as the `restapi` and `mcp` templates.
- **Starlette, not FastAPI**: `a2a.server.routes.create_agent_card_routes`, `create_jsonrpc_routes`, and `create_rest_routes` return `list[starlette.routing.Route]`; the `mcp` template already uses Starlette; FastAPI would only add `/docs`. `a2a-sdk[http-server]` brings `starlette` and `sse-starlette`; uvicorn is added separately.
- **`entry_points` in the base `INJECTABLES`**: `driven_adapters`, `helpers` and `usecases` are already scanned as whole layers; scanning `entry_points` the same way registers any entry-point factory (A2A today, e.g. a Kafka consumer later) without `gep` ever editing `wiring.py`, and keeps a single composition point that `test_wiring.py` validates. The wireup layout of spec 028 is not released yet, so no shipped project lacks the entry; development projects created before this change (e.g. `library_aiagent/`) add `entry_points` by hand. Cost: the scan imports every module under `entry_points/` at container creation, so those modules must stay free of import-time side effects; the e2e scenarios for every `gep` type cover this.
- **Routes in the lifespan**: `DefaultRequestHandler` requires the `AgentCard`, and `AsyncContainer.get` is async, so the handler can only be resolved after startup. An `app.state` flag keeps the mount idempotent when `TestClient` re-enters the lifespan.
- **Kafka and MCP client removed**: the old flags only added commented stubs to a class that no longer exists. They are deferred to future features (FR-046).

**Alternatives considered**:
- Keep the stub agent class with `asyncio.run` → rejected: never starts a server.
- Own container in `app.py` (`create_async_container(injectables=[*INJECTABLES, a2a_server])`) → first implementation, replaced: two composition points, and `test_wiring.py` would not validate the A2A graph.
- Edit `wiring.py` (`insert_after` on a multi-line `INJECTABLES`) → rejected: needs a per-type edit and an anchor format that older projects lack.
- New `ReplaceText` file operation in the core → rejected: more API surface for a single use.
- FastAPI app with `app.mount(...)` → rejected: heavier dependencies and no benefit for the SDK-generated routes.

**Validated in prototype**: `library_aiagent/` (hand-written with a2a-sdk 1.1.5, wireup 2.13) serves the agent card and answers JSON-RPC `SendMessage`. Facts confirmed against the installed SDK: `DefaultRequestHandler(agent_executor, task_store, agent_card)`; `AgentCard` uses `supported_interfaces=[AgentInterface(url, protocol_binding, protocol_version)]` (no `url` field); `TaskUpdater.add_artifact` must precede the terminal status event; `wireup.integration.starlette.setup()` wraps the lifespan and closes the container on shutdown; JSON-RPC and REST (`POST /message:send`) require the `A2A-Version: 1.0` header; `EventQueue` is abstract (tests use a collecting subclass); `RequestContext.task_id`/`context_id` are typed `str | None`.

---

## Wireup error messages (measured in spike)

| Situation | Error |
|-----------|-------|
| Gateway has no implementation | `WireupError: Parameter '<param>' of <UseCase> has an unknown dependency on <Gateway>` |
| Ambiguous implementations | `WireupError: Multiple implementations registered for <Gateway>` |
| Unknown config key | `WireupError: unknown Wireup config key '<key>'` |
| Async resource in sync container | `WireupError: <Adapter> is an async dependency and it cannot be created in a synchronous context` |
| `Inject` imported under `TYPE_CHECKING` | `NameError: name 'Inject' is not defined` (annotations evaluated at runtime by wireup) |

The last error is why the `TC` ruff rule must be disabled in generated projects (it would move `Inject`/`Injected` under `TYPE_CHECKING`).

---

## Decision: wiring tests use one module-level strict xfail

Wireup validates the entire dependency graph inside `create_container()`. A single gateway without an adapter therefore makes **every** test in `test_wiring.py` raise `WireupError`, not just the test for the affected use case. A per-function marker would be wrong, so the generated module defines `MISSING_ADAPTERS` and one `pytestmark = pytest.mark.xfail(bool(MISSING_ADAPTERS), raises=WireupError, strict=True)`. `strict=True` turns a stale list (adapter added by hand) into an XPASS failure, preserving the fail-fast guarantee of SC-003 while keeping `pytest` green in the intermediate state. The scaffolder recomputes the list in `guc`, `gda` and `dm`.

---

## wireup and libcst maintenance status (as of 2026-10-29)

- **wireup**: last release 2.13.0 (recent); Python 3.13+ tested; pure Python (no Cython), so new Python versions are low-risk.
- **libcst**: actively maintained by Meta; supports Python 3.13; widely used in the Python migration-tool ecosystem.
