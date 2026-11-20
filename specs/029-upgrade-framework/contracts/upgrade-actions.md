# Contract: `scaffold up` upgrade actions

**Feature**: 029-upgrade-framework (see [spec.md](../spec.md))

---

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | bool | `False` | Print unified diffs and report; write nothing |
| `--skip-upgrades` | bool | `False` | Run only `uv lock --upgrade` and `uv sync` |
| `--report` | `json` \| `text` | `text` | Structured report for applied and pending items |
| `--allow-dirty` | bool | `False` | Allow writes when the git tree is dirty |

`install-skill` is **not** a flag on `up`; see [install-skill contract](#install-skill) below.

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (including success with pending manual items in the report) |
| `1` | Any failure: precondition, upgrade action error, or `uv` subprocess failure |

All failures use code `1` (consistent with `fail()` elsewhere). Typer may still use `2` for usage errors.

---

## `--report json` Schema

```jsonc
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["automated", "pending", "scaffold_version"],
  "properties": {
    "scaffold_version": {
      "type": "object",
      "required": ["declared", "installed"],
      "properties": {
        "declared": { "type": ["string", "null"] },
        "installed": { "type": "string" },
        "newer_than_installed": { "type": "boolean" }
      }
    },
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
      "items": { "$ref": "pending-item.schema.json" }
    },
    "actions_run": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["name", "applied", "skipped"],
        "properties": {
          "name": { "type": "string" },
          "applied": { "type": "boolean" },
          "skipped": { "type": "boolean" },
          "reason": { "type": "string" }
        }
      }
    }
  }
}
```

Pending item shape: [pending-items.md](pending-items.md).

---

## Stdout / stderr contract

- With `--report json`, **stdout** contains only the JSON document (no Rich banners, no `uv` logs).
- **stderr** receives human progress, `uv` output, warnings (e.g. newer `scaffold_version`), and Rich formatting.

---

## Execution order (non–dry-run)

1. Load `ProjectContext`; evaluate version guard (FR-010).
2. Enforce clean tree when applicable (FR-003).
3. For each action in `UPGRADE_ACTIONS` where `applies(builder)` is true: run `up(builder)`; call `persist_and_format` after each action (see plan limitations for dry-run).
4. `uv lock --upgrade`
5. `uv sync`
6. If any action wrote files, set `scaffold_version` to installed version (when not dry-run).

---

## `install-skill`

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--target` | `claude` \| `cursor` \| `agents` \| `all` | `all` | Destination skill directories |
| `--force` | bool | `False` | Overwrite existing skill tree |

Exit `0` on success; exit `1` on failure. Does not modify application source except skill paths and `AGENTS.md`.