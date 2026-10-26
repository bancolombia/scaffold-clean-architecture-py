# CLI Contract changes: `scaffold dm` / `scaffold delete-module`

Only the model lookup changes. Flags, messages, and exit codes stay the same.

## Model candidates (in order)

| Layout | Source target | Test target |
|---|---|---|
| Package (new) | `src/<pkg>/domain/model/<name>/` (directory) | `src/tests/domain/model/<name>/` (directory, if present) |
| Flat (legacy) | `src/<pkg>/domain/model/<name>.py` | `src/tests/domain/model/test_<name>.py` (if present) |

## Outcomes for models

| Situation | Exit | Effect |
|---|---|---|
| `dm --name x` (no `--confirm`) or `--dry-run` | 0 | preview lists the package dir and the tests dir; nothing is removed |
| `dm --name x --confirm`, package layout | 0 | both directories are removed recursively |
| `dm --name x --confirm`, legacy layout | 0 | flat model file and flat test file are removed, as today |
| no match | 1 | existing "No module named ..." error |
