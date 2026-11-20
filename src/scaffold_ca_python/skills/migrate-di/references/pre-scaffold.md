# Projects created before the scaffolder

Services written before scaffold-ca-python often share the Clean Architecture layout and dependency-injector containers but differ in conventions. `scaffold up` still does the mechanical part; most of the remaining work is design and needs the user's decisions.

## 0. Adopt the project

1. Commands exit with `<path>/pyproject.toml has no [tool.scaffold-ca-python] section` and print the block to add. Add it **without** `scaffold_version` (that key marks a migrated project):

   ```toml
   [tool.scaffold-ca-python]
   name = "my-service"        # kebab-case of the package under src/ (src/my_service)
   ```

2. Confirm the layout: `src/<pkg>/{domain,application,infrastructure}` and tests under `src/tests/` (or `tests/`). If the package name is not the snake case of `name`, stop and ask the user: renaming the package is out of scope.
3. Record the baseline: `uv run pytest` must pass before migrating.

Recognized naming variants: use cases under `domain/usecase/`, `usecases/`, `use_case/` or `use_cases/`; gateways under `.../gateways/` or `.../gateway/`. Other differences (e.g. tests in `test_domain/`) do not block the migration.

## 1. Run the migration

`scaffold up --dry-run --report json`, then `scaffold up` after approval (see `SKILL.md`). Expect many more pending items than in a 0.5.0 project. Resolve them in this order: adapters' configuration → resources → use cases → composition root → tests.

## 2. Configuration passed by value (`provider_arguments`)

Pre-scaffold containers often build adapters with settings values:

```python
aws_s3_adapter = providers.Singleton(
    S3Adapter, storage_client=resource_container.storage_client, bucket_name=settings.CODE_REVIEW_BUCKET_INPUT
)
```

wireup injects by type, so give each adapter a typed settings class next to it and inject that:

```python
# infrastructure/driven_adapters/aws/s3_settings.py
class S3Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CODE_REVIEW_")
    bucket_input: str


@wireup.injectable
def s3_settings() -> S3Settings:
    return S3Settings()


# s3_adapter.py
@wireup.injectable(as_type=StoreRepository)
class S3Adapter(StoreRepository):
    def __init__(self, storage_client: S3, settings: S3Settings) -> None: ...
```

- Keep the existing environment variable names (`env_prefix`, `validation_alias`) so deployments do not change; **ask the user** before renaming any variable.
- Dict/literal arguments (`config={...}`) become fields of the settings class.
- One settings class per adapter (or per external system), not one global class injected everywhere.

## 3. Resources and factory functions (`resource_provider`, `callable_provider`)

- Generator resources (`aiohttp.ClientSession`, DB pools, MCP clients) → `@wireup.injectable` generator/async-generator functions returning the resource type; teardown after `yield`.
- Plain factory functions (`boto3_session()`, `get_github_token(...)`) → `@wireup.injectable` functions with typed parameters.
- Environment-conditional providers (`if settings.ENV == "local": ...`) → one factory that branches on a settings field. Confirm the branches with the user.
- Third-party types used as dependencies must be the factory's return annotation (e.g. `-> boto3.session.Session`).

## 4. Container tests (`override_in_test`)

Tests that instantiate `Container()` or check providers (`test_container.py`, `test_*_container.py`) test dependency-injector itself. Replace them with `src/tests/application/config/test_wiring.py` (created by `scaffold up`) plus factory tests; delete the old ones after the user agrees. Tests that override providers move to `container.override.injectable(target=..., new=...)`.

## 5. Custom composition roots (`composition_root_modified`)

- **MCP (FastMCP + `bind_tools`)**: build `create_container()` in the lifespan; register tools with `wireup.integration` helpers or resolve the use case with `await container.get(UseCase)` once and pass it to `bind_tools`. Remove `container.wire(...)`, `init_resources()` and `shutdown_resources()`; call `await container.close()` on shutdown.
- **A2A / Starlette**: `wireup.integration.starlette.setup(create_container(), app)` after the routes are defined; resolve the request handler from the container in the lifespan.
- Keep middleware, auth, observability (e.g. traceloop) and routes exactly as they are.

## Stop conditions specific to pre-scaffold projects

- Renaming packages, environment variables or public routes.
- Choosing between two implementations of the same gateway.
- Deleting tests that are not purely about the legacy container.
- Upgrading unrelated libraries (e.g. `a2a-sdk` major versions) — out of scope for this migration.
