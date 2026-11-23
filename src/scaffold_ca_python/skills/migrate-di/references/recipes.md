# Recipes by pending kind

Each heading is a pending `kind` emitted by `scaffold up --report json`. The full guide with examples is `docs/migration/dependency-injector-to-wireup.md` in scaffold-ca-python (anchor = `guide_section`).

## resource_provider

`providers.Resource(fn)` → put `@wireup.injectable` on `fn` (a generator or async generator function returning `Iterator[T]` / `AsyncIterator[T]`), import `wireup` in that module, then delete the container file once it holds nothing else. Consumers request `T` by type.

## configuration_provider

Replace `providers.Configuration()` with a `pydantic-settings` class next to the adapter. Register it with an `@wireup.injectable` factory returning `Settings()` and inject the settings type into the adapter constructor.

## selector_provider

Write one `@wireup.injectable(as_type=<Gateway>)` factory that picks the implementation (e.g. from settings), or decorate exactly one implementation with `as_type`.

## callable_provider

Write an explicit `@wireup.injectable` factory that returns the object: under `application/config/usecases/` for use cases, next to the adapter for infrastructure objects.

## nested_container

Flatten each provider of the nested container into a factory module or an `@wireup.injectable` class, then delete the nested container.

## provider_arguments

The binding passes non-provider values (settings fields, literals, positional args) or the constructor has unannotated parameters. Give the class a typed settings dependency instead of loose values: create `<Name>Settings(BaseSettings)` next to it (keep the current environment variable names), register an `@wireup.injectable` factory returning it, change the constructor to take the settings object, then decorate the class with `@wireup.injectable(as_type=<Gateway>)`. Annotate any remaining parameter with an injectable type. Delete the container entry afterwards. Full example: `references/pre-scaffold.md` §2.

## override_in_test

Replace `container.<x>.override(fake)` / `app.state.container` with `get_app_container(client.app).override.injectable(target=<Type>, new=fake)` (a context manager, inside `with TestClient(create_app()) as client:`), or build the unit under test directly with fakes.

## usecase_uses_helper

Add a gateway ABC in `domain/model/<model>/gateways/`, make the helper implement it with `@wireup.injectable(as_type=<Gateway>)`, and type the use-case parameter with the gateway.

## injection_unresolved

Annotate the parameter as `Injected[T]` (from `wireup import Injected`), move it before parameters that have defaults, remove `@inject`, `Provide` and `Container` imports.

## composition_root_modified

Port the file to the 1.0.0 pattern: build `create_container()` from `application/config/wiring.py`, call `wireup.integration.fastapi.setup(container, app)` in the lifespan and `await container.close()` on shutdown. Keep the user's custom routes, middleware and handlers.
