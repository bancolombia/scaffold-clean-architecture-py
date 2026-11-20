# Contract: pending manual items

**Feature**: 029-upgrade-framework

Canonical item kinds for the dependency-injector → wireup upgrade action. The source of truth in code is `PENDING_KINDS` / `AUTOMATED_KINDS` in `src/scaffold_ca_python/factory/upgrades/report.py`; constructing an item with any other kind raises. `tests/factory/upgrades/test_kinds_alignment.py` keeps this table, `skills/migrate-di/references/recipes.md` (one `## <kind>` heading per kind) and `docs/migration/dependency-injector-to-wireup.md` (one `<a id="<guide_section>">` anchor per kind) in sync.

---

## Item shape

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `kind` | string (enum below) | yes | Stable key for recipes and tests |
| `file` | string | yes | Project-relative POSIX path (e.g. `src/<pkg>/application/app.py`) |
| `line` | integer ≥ 1 | yes | 1-based line number |
| `guide_section` | string | yes | Anchor in `docs/migration/dependency-injector-to-wireup.md`; derived from `kind` |
| `suggested_skeleton` | string | no | Omitted when there is no starter code |

JSON Schema (referenced by [upgrade-actions.md](upgrade-actions.md)):

```jsonc
{
  "type": "object",
  "required": ["kind", "file", "line", "guide_section"],
  "properties": {
    "kind": { "enum": ["resource_provider", "configuration_provider", "selector_provider", "callable_provider", "nested_container", "provider_arguments", "override_in_test", "usecase_uses_helper", "injection_unresolved", "composition_root_modified"] },
    "file": { "type": "string" },
    "line": { "type": "integer", "minimum": 1 },
    "guide_section": { "type": "string" },
    "suggested_skeleton": { "type": "string" }
  },
  "additionalProperties": false
}
```

---

## `pending` kinds

| kind | guide_section | Typical trigger |
|------|---------------|-----------------|
| `resource_provider` | `providers-resource` | `providers.Resource(...)` in a container |
| `configuration_provider` | `providers-configuration` | `providers.Configuration()` |
| `selector_provider` | `providers-selector` | `providers.Selector(...)` |
| `callable_provider` | `providers-callable` | `providers.Callable/Object/List/...`, or a binding to a class outside the project package |
| `nested_container` | `nested-container` | Nested `DeclarativeContainer`, or `providers.Container(X)` where `X` is not one of the project's containers |
| `provider_arguments` | `provider-arguments` | Binding with non-provider arguments (settings fields, literals, positional args) or a constructor parameter without annotation |
| `override_in_test` | `override-in-test` | Tests calling `.override(...)` / `.override_providers(...)`, touching `app.state.container`, or importing the legacy DI |
| `usecase_uses_helper` | `usecase-uses-helper` | Use-case constructor typed with a class from `infrastructure.helpers` |
| `injection_unresolved` | `injection-unresolved` | `Provide[...]` parameter without annotation or after a defaulted parameter; a module that still imports `dependency_injector` / the root `Container` after rewriting; an unparsable container |
| `composition_root_modified` | `composition-root` | A bootstrap module (`src/<pkg>/*.py`, `src/<pkg>/application/*.py`) that uses the legacy container and does not match the 0.5.0 restapi render |

A container module is deleted only when none of its providers produced a pending item; otherwise it stays on disk so the next `scaffold up` reports it again.

## `automated` kinds

| kind | Meaning |
|------|---------|
| `pyproject_update` | Dependency swap, `mypy` dev dependency, ruff/pytest keys, `scaffold_version` |
| `wiring_created` | `application/config/wiring.py` (package-scan `INJECTABLES`) |
| `wiring_test_created` | `src/tests/application/config/test_wiring.py` with `MISSING_ADAPTERS` computed |
| `container_to_factory` | `application/config/usecases/<module>.py` factory from a use-case binding |
| `container_removed` | Fully migrated container module deleted |
| `injectable_on_adapter` | `@wireup.injectable[(as_type=..., lifetime=...)]` added to an adapter/helper class |
| `provide_to_injected` | `Provide`/`Depends(Provide[...])` → `Injected[T]`, `@inject` and legacy imports removed |
| `composition_root_replaced` | 0.5.0 restapi `application/app.py` / `src/tests/application/test_app.py` replaced (SHA-256 match) |
| `scaffold_version_updated` | Runner aligned an existing `scaffold_version` with the installed scaffolder |

---

## Example JSON fragment

```json
{
  "pending": [
    {
      "kind": "resource_provider",
      "file": "src/legacy_fixture/application/config/resource_container.py",
      "line": 10,
      "guide_section": "providers-resource"
    }
  ]
}
```
