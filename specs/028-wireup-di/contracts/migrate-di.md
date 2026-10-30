# Contract: `scaffold migrate-di` Interface

**Feature**: 028-wireup-di

---

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | bool | `False` | Print diff + report; write nothing |
| `--yes` | bool | `False` | Apply all automated transforms without prompting |
| `--report` | `json` \| `text` | `text` | Output format for the pending-items report |
| `--install-skill` | bool | `False` | Copy the agent skill to the target project |
| `--target` | `claude` \| `cursor` \| `agents` \| `all` | `all` | Which skill directories to populate |
| `--force` | bool | `False` | Overwrite an existing installed skill |

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | No changes needed (project already migrated or `--dry-run`) |
| `1` | Changes applied; no pending manual items; post-verification passed |
| `2` | Changes applied; pending manual items remain (see report) |
| `3` | Precondition failure (dirty git tree, not a legacy project, etc.) |
| `4` | Changes applied but post-verification (`uv sync` / ruff / mypy / pytest) failed |

---

## `--report json` Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["automated", "pending"],
  "properties": {
    "automated": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kind", "file"],
        "properties": {
          "kind": { "type": "string" },
          "file": { "type": "string" },
          "description": { "type": "string" }
        }
      }
    },
    "pending": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["kind", "file", "line", "guide_section"],
        "properties": {
          "kind": {
            "type": "string",
            "enum": [
              "resource_provider",
              "configuration_provider",
              "selector_provider",
              "callable_provider",
              "nested_container",
              "override_in_test",
              "usecase_uses_helper",
              "composition_root_modified"
            ]
          },
          "file": { "type": "string", "description": "repo-relative path" },
          "line": { "type": "integer", "minimum": 1 },
          "guide_section": {
            "type": "string",
            "description": "anchor in docs/migration/dependency-injector-to-wireup.md"
          },
          "suggested_skeleton": {
            "type": "string",
            "description": "optional code skeleton to get started"
          }
        }
      }
    }
  }
}
```

---

## `--report json` Example Output

```json
{
  "automated": [
    { "kind": "pyproject_update", "file": "pyproject.toml", "description": "wireup dependency and scaffold_version key written" },
    { "kind": "container_to_factory", "file": "application/config/usecases/create_order_usecase.py", "description": "generated from providers.Singleton(CreateOrderUseCase, ...)" },
    { "kind": "injectable_on_adapter", "file": "infrastructure/driven_adapters/in_memory_order/in_memory_order_adapter.py", "description": "@injectable(as_type=OrderRepository) added" },
    { "kind": "provide_to_injected", "file": "infrastructure/entry_points/api/v1/rest_controller.py", "description": "Provide[...] → Injected[...] on 2 parameters" }
  ],
  "pending": [
    {
      "kind": "resource_provider",
      "file": "application/config/resource_container.py",
      "line": 14,
      "guide_section": "providers-resource",
      "suggested_skeleton": "# In infrastructure/driven_adapters/my_db/my_db_config.py:\nfrom wireup import injectable\nfrom collections.abc import AsyncIterator\n\n@injectable\nasync def make_my_db_pool(settings: MyDbSettings) -> AsyncIterator[MyDbPool]:\n    pool = await MyDbPool.connect(settings.dsn)\n    yield pool\n    await pool.close()"
    }
  ]
}
```

---

## Idempotency Contract

Running `migrate-di --yes` on a project that already has `scaffold_version = "<version>"` in `pyproject.toml`:

- Must print "Project is already on wireup; nothing to do."
- Must exit `0`.
- Must not modify any file.

---

## Precondition Checks (performed before any write)

1. `[tool.scaffold-ca-python]` section exists in `pyproject.toml`.
2. `scaffold_version` key is absent from `[tool.scaffold-ca-python]` (project is legacy; ≤ 0.5.0 projects never had this key).
3. `git status --porcelain` output is empty (working tree clean).

If any check fails, exit `3` with a human-readable error and a resolution hint.

**Note**: The `require_wireup_project` guard in `generate-*` commands checks for the same `scaffold_version` key — a project is legacy iff the key is absent. `migrate-di` uses the same criterion as its precondition.
