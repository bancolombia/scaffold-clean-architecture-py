# Migrating a 0.5.0 project from dependency-injector to wireup

Projects generated with scaffold-ca-python **≤ 0.5.0** wire dependencies with `dependency-injector` declarative containers. Since **1.0.0** the scaffolder generates [wireup](https://github.com/maldoinc/wireup) projects and refuses to modify legacy ones. `scaffold up` migrates a legacy project; this guide explains what it automates and how to finish the rest.

## Quick path

```bash
git status                       # start from a clean tree (or pass --allow-dirty)
scaffold up --dry-run            # review the unified diff and the pending list
scaffold up                      # apply, then uv lock --upgrade + uv sync
scaffold up --report json        # machine-readable report (stdout is JSON only)
```

Every pending item names a `guide_section`: the anchors below. Run `scaffold up` again at any time; it rewrites nothing that is already migrated and re-reports what is still pending. When nothing legacy remains, the action is skipped.

For agent-guided completion: `scaffold install-skill migrate-di`.

## Projects created before the scaffolder

Services written before scaffold-ca-python can use the same tools when they follow the Clean Architecture layout (`src/<pkg>/{domain,application,infrastructure}`) with dependency-injector containers.

1. **Adopt.** Without `[tool.scaffold-ca-python]`, every command exits 1 with `<path>/pyproject.toml has no [tool.scaffold-ca-python] section` and prints the block to add. Add it **without** `scaffold_version`:

   ```toml
   [tool.scaffold-ca-python]
   name = "my-service"   # kebab-case of the package under src/ (src/my_service)
   ```

2. **Migrate** with the quick path above. Use cases under `domain/usecase/`, `usecases/`, `use_case/` or `use_cases/` and gateways under `gateways/` or `gateway/` are recognized.
3. **Expect more manual work** than in a 0.5.0 project. These services usually pass configuration by value (`bucket_name=settings.X`), build resources with plain functions, have hand-written MCP/A2A composition roots and tests that exercise the containers directly. Those show up as `provider_arguments`, `resource_provider`/`callable_provider`, `composition_root_modified` and `override_in_test`. The skill reference `references/pre-scaffold.md` (`scaffold install-skill migrate-di`) explains how to turn them into typed settings classes, wireup factories and `test_wiring.py`, and when to stop and ask.

Migrating the DI does not rename the project's packages. If you plan to keep generating code with `gm`/`guc`/`gda`, align the folder names with the scaffolder's (`domain/usecase/`, `gateways/`) as a separate change.

## What `scaffold up` automates

| Before (0.5.0) | After (1.0.0 layout) |
|---|---|
| `dependency-injector==4.x` in `[project].dependencies` | `wireup~=2.13`; `mypy` in the `dev` group; ruff `ASYNC` selected and `TC` ignored; pytest `asyncio_mode = "auto"`; `scaffold_version` written |
| `application/config/container.py` and `*_container.py` | Deleted once every provider in the file is migrated; `application/config/wiring.py` (package-scan `INJECTABLES`) and `application/config/usecases/__init__.py` created |
| `providers.Singleton(UseCase, repo=da_container.repo)` | `application/config/usecases/<module>.py` with an `@wireup.injectable` factory built from the use case's `__init__` signature |
| `providers.Singleton(Adapter)` / `providers.Factory(Adapter)` | `@wireup.injectable(as_type=<Gateway>)` on the adapter or helper class (`lifetime="transient"` for `Factory`) |
| `use_case: UC = Depends(Provide[Container.x])` + `@inject` | `use_case: Injected[UC]`; `@inject`, `Provide`, `Container` and unused `Depends` imports removed |
| 0.5.0 restapi `application/app.py` and `src/tests/application/test_app.py`, unmodified | Replaced by the 1.0.0 templates (`wireup.integration.fastapi.setup` in the lifespan). Replacement only happens on a SHA-256 match with the 0.5.0 render for the same project name |
| — | `src/tests/application/config/test_wiring.py`: builds the whole graph; fails fast when a gateway has no adapter |

Untouched files are not reformatted. 0.5.0 never auto-formatted generated files, so run `uv run ruff format .` once after migrating (checklist step 1).

### Lifecycle equivalence

| dependency-injector | wireup |
|---|---|
| `providers.Singleton` | `@wireup.injectable` (default lifetime `singleton`) |
| `providers.Factory` | `@wireup.injectable(lifetime="transient")` |
| `providers.Resource` (generator / async generator) | `@wireup.injectable` on a generator factory; teardown runs on `await container.close()` |
| `container.wire(modules=[...])` | Not needed: `Injected[T]` parameters are resolved by the framework integration |
| `container.init_resources()` / `shutdown_resources()` | `create_container()` / `await container.close()` (the FastAPI template does both in the lifespan) |

## Pending items

<a id="providers-resource"></a>
### `resource_provider`: `providers.Resource(...)`

Turn the resource function into a wireup factory and delete the container once it is empty.

```python
# infrastructure/helpers/clock/clock.py
import wireup

@wireup.injectable
def open_clock() -> Iterator[Clock]:      # AsyncIterator[...] for async resources
    clock = Clock()
    yield clock
    # teardown here
```

Consumers request `Clock` by type. Then delete the file that only held the resource (for example `application/config/resource_container.py`).

<a id="providers-configuration"></a>
### `configuration_provider`: `providers.Configuration()`

Replace configuration keys with a typed `pydantic-settings` class next to the adapter that uses it. Register it with an `@wireup.injectable` factory that returns `Settings()`, then inject the settings type into the adapter constructor.

<a id="providers-selector"></a>
### `selector_provider`: `providers.Selector(...)`

wireup resolves by type. Pick the implementation in a factory, for example based on settings, and register that factory with `@wireup.injectable(as_type=<Gateway>)`. Alternatively, decorate exactly one implementation with `as_type`.

<a id="providers-callable"></a>
### `callable_provider`: `providers.Callable`, `Object`, `List`, … or classes outside the project

Write an explicit `@wireup.injectable` factory function under `application/config/usecases/` (use cases) or next to the adapter (infrastructure) that returns the built object.

<a id="nested-container"></a>
### `nested_container`: nested or external `DeclarativeContainer`

Flatten each provider into a factory module or an `@wireup.injectable` class. wireup has a single container built from package scan, so nesting is not needed.

<a id="provider-arguments"></a>
### `provider_arguments`: arguments that cannot be injected by type

The binding passes values that are not other providers, such as `settings.URL`, literals or positional arguments. The other case is a constructor parameter without a type annotation. wireup injects by type only, so do one of:

- annotate the parameter with a gateway or settings type that has an injectable;
- write the factory by hand and read the values from a settings class.

The container stays on disk until the item is resolved.

<a id="override-in-test"></a>
### `override_in_test`: container overrides in tests

Replace `container.x.override(fake)` and `app.state.container` access with wireup overrides:

```python
from wireup.integration.fastapi import get_app_container

with TestClient(create_app()) as client:
    container = get_app_container(client.app)
    with container.override.injectable(target=BookRepository, new=FakeBookRepository()):
        response = client.get("/v1/books/1")
```

For unit tests, construct the use case directly with a fake.

<a id="usecase-uses-helper"></a>
### `usecase_uses_helper`: use case depends on an infrastructure helper

Use cases may only depend on domain gateways. Declare a gateway ABC in `domain/model/<model>/gateways/`, make the helper implement it with `@wireup.injectable(as_type=<Gateway>)`, and type the use case parameter with the gateway.

<a id="injection-unresolved"></a>
### `injection_unresolved`: injection the codemod could not rewrite

This happens when a `Provide[...]` parameter has no type annotation, follows a parameter that has a default, or the module still imports `dependency_injector` / the root `Container`. Annotate the parameter as `Injected[T]`, place it before parameters with defaults, and remove the legacy imports.

<a id="composition-root"></a>
### `composition_root_modified`: edited or unsupported composition root

`application/app.py`, `main.py` or another bootstrap module still builds the legacy `Container`. Port the edits onto the 1.0.0 pattern:

```python
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    container = create_container()
    wireup.integration.fastapi.setup(container, app)
    yield
    await container.close()
```

MCP and generic entry points follow the same idea with `create_container()` from `application/config/wiring.py`; generate a fresh 1.0.0 entry point (`scaffold gep --type ...` in a scratch project) to copy from.

## Common errors

| Error | Cause | Fix |
|---|---|---|
| `WireupError: Parameter 'x' of F has an unknown dependency on G` | No injectable provides `G` | Add `@wireup.injectable(as_type=G)` to an adapter, or `scaffold gda --gateway` |
| `WireupError: Multiple implementations registered for G` | Two classes declare `as_type=G` | Keep one, or use a qualifier |
| `NameError: name 'Injected' is not defined` | `Injected` imported under `TYPE_CHECKING` | Import at runtime; keep ruff `TC` ignored |
| `ModuleNotFoundError: dependency_injector` | A module still imports the legacy package | Resolve the remaining pending items |
| `test_wiring.py` XPASS (strict) | `MISSING_ADAPTERS` lists a gateway that now has an adapter | Remove it from the list |

## Verification checklist

1. `uv run ruff check --fix --select I . && uv run ruff format .` (once; 0.5.0 files were never formatted)
2. `uv sync`
3. `uv run ruff check .` and `uv run ruff format --check .`
4. `uv run mypy --strict src/`
5. `uv run pytest`
6. `scaffold vs`
7. `scaffold up --dry-run --report json` shows an empty `pending` list and the action as skipped

## Rollback

`scaffold up` requires a clean git tree by default precisely so that the migration is one reviewable diff:

```bash
git stash push --include-untracked -m "scaffold up migration"   # set the migration aside (reversible)
git stash pop                                                    # bring it back later
```

The command never commits. With `--allow-dirty`, inspect `git diff` before committing.
