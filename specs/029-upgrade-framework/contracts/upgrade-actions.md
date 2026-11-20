# Contract: `scaffold up` upgrade actions

**Feature**: 029-upgrade-framework (see [spec.md](../spec.md))

---

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--dry-run` | bool | `False` | Print unified diffs and report; write nothing |
| `--skip-upgrades` | bool | `False` | Run only `uv lock --upgrade` and `uv sync` |
| `--report` | `json` \| `text` | `text` | Structured report for applied and pending items |
| `--allow-dirty` | bool | `False` | Allow writes when the git tree is dirty, or when cleanliness cannot be verified (not a git repository / git missing) |

`install-skill` is **not** a flag on `up`; see [install-skill contract](#install-skill) below.

---

## Project detection

`scaffold up` (like every project command) needs `[tool.scaffold-ca-python]` in `pyproject.toml`. When the nearest `pyproject.toml` lacks it, the command exits `1` with:

```
<path>/pyproject.toml has no [tool.scaffold-ca-python] section.
If this is a Clean Architecture project, add:

[tool.scaffold-ca-python]
name = "<kebab-case of the src/ package>"

then run `scaffold up --dry-run` to migrate it (see docs/migration/dependency-injector-to-wireup.md).
```

The same message is shown when the command runs inside `src/<pkg>/`.

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
      "items": { "$ref": "pending-items.md#item-shape" }
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

- With `--report json`, **stdout** contains only the JSON document (no Rich banners, no `uv` logs, no diffs).
- **stderr** receives human progress, `uv` output, warnings (e.g. newer `scaffold_version`), errors from `fail()`, and the dry-run unified diffs.
- In text mode, dry-run diffs are written verbatim (no Rich markup or wrapping) to stdout. Paths in diffs and report items are project-relative (`a/<path>`, `b/<path>`, `/dev/null` for created/deleted files).

---

## Execution order (non–dry-run)

1. Load `ProjectContext`; if the declared `scaffold_version` is newer than the installed scaffolder, warn and skip every action (FR-010).
2. If any action `applies()` and `--allow-dirty` is not set: require `git status --porcelain` to be empty; a non-repository or missing git also fails with exit `1` (FR-003).
3. For each action in `UPGRADE_ACTIONS` (registry order) whose `applies(builder)` is true: `up(builder)` queues operations, then `builder.persist()` writes them before the next action is evaluated.
4. If any action applied changes and `pyproject.toml` already declares a different `scaffold_version`, the runner sets it to the installed version (report item `scaffold_version_updated`). The dependency-injector action writes `scaffold_version` itself as part of its pyproject edit, so the key is written exactly once per run.
5. Format only the files written in step 3–4 (`ruff check --fix --select I` + `ruff format` on those paths).
6. `uv lock --upgrade`
7. `uv sync`

Dry-run performs steps 1 and 3 with a dry-run builder (no writes, diffs collected), prints the planned `uv` commands, and skips steps 2 and 4–7.

---

## `install-skill`

```
scaffold install-skill <skill> [--target claude|cursor|agents|all] [--force]
```

| Argument / flag | Default | Description |
|------|---------|-------------|
| `<skill>` | — | Must be one of the skills packaged in the wheel (`scaffold_ca_python/skills/<name>/SKILL.md`); any other value, including paths, exits `1` |
| `--target` | `all` | `.claude/skills/`, `.cursor/skills/`, `.agents/skills/`, or all three |
| `--force` | `False` | Replace an existing `<target>/<skill>/` directory |

- Without `--force`, an existing installation is kept with a warning and the remaining targets are still processed; exit `0`.
- `AGENTS.md` (created if missing) gets one `- \`<skill>\`: <installed SKILL.md paths>` line under a `## Skills` section; repeated runs do not duplicate it.
- Application source is never modified.
