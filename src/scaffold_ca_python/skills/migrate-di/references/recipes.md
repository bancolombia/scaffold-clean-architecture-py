# Recipes by pending kind

| kind | Recipe |
|------|--------|
| resource_provider | Add async factory module per D6; wire via `@injectable` factory. |
| configuration_provider | Move settings to `pydantic-settings` and use constructor injection. |
| selector_provider | Choose single implementation manually; add `@injectable(as_type=...)`. |
| callable_provider | Replace with wireup factory function in `application/config/usecases/`. |
| factory_provider | Same as `callable_provider` (providers.Factory → transient factory). |
| nested_container | Flatten into separate factory modules. |
| override_in_test | Use wireup test overrides or explicit fakes in tests. |
| usecase_uses_helper | Remove helper from use case; define a gateway port instead. |
| composition_root_modified | Merge manual `application/app.py` changes into wireup lifespan pattern. |
| override_in_test | Replace container overrides with explicit test doubles or wireup test helpers. |
| usecase_uses_helper | Remove helper from use case; define a gateway port instead. |
| nested_container | Flatten nested containers into separate factory modules. |
