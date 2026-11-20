# Contract: pending manual items

**Feature**: 029-upgrade-framework

Canonical pending-item kinds for the dependency-injector → wireup upgrade action (inherited from the retired `migrate-di` draft, adapted for `scaffold up`).

---

## Item shape

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `kind` | string (enum) | yes | Stable key for recipes and tests |
| `file` | string | yes | Repo-relative path |
| `line` | integer ≥ 1 | yes | 1-based line number |
| `guide_section` | string | yes | Anchor in `docs/migration/dependency-injector-to-wireup.md` |
| `suggested_skeleton` | string | no | Optional starter code |

---

## `kind` enum

| kind | Typical trigger |
|------|------------------|
| `resource_provider` | `providers.Resource` in a container |
| `configuration_provider` | `providers.Configuration` |
| `selector_provider` | `providers.Selector` |
| `callable_provider` | `providers.Callable` / custom factory |
| `nested_container` | Nested `DeclarativeContainer` |
| `override_in_test` | Test overrides of container providers |
| `usecase_uses_helper` | Use case wiring a helper against domain rules |
| `composition_root_modified` | Composition root / `main` not matching 0.5.0 fingerprint |

Additional kinds for automated lines (report `automated` array, not `pending`): `pyproject_update`, `container_to_factory`, `injectable_on_adapter`, `provide_to_injected`, `wiring_created`, `container_removed`.

---

## Example JSON fragment

```json
{
  "pending": [
    {
      "kind": "composition_root_modified",
      "file": "application/app.py",
      "line": 1,
      "guide_section": "composition-root",
      "suggested_skeleton": null
    }
  ]
}
```