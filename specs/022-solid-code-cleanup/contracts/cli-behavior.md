# Contract: observable CLI behavior

This refactor does **not** change the public interface. The contract is what the suite already verifies, plus the three explicit exceptions listed at the end.

## Invariants

| Aspect | Contract | Verified by |
|---|---|---|
| Commands and aliases | `ca/clean-architecture`, `gm`, `guc`, `gda`, `gep`, `gh`, `gpipe`, `vs`, `dm`, `up`, with the same long names | `tests/commands/test_cli.py` |
| Flags and defaults | Same names, defaults, help panels and epilogs | `--help` snapshot in `test_cli.py` and per-command tests |
| Generated files | Byte-for-byte identical, including the files that now come from new templates (FR-004) | `tests/commands/test_dry_run_checksum.py`, `tests/templates/` |
| `--dry-run` | Same list of paths, no writes | `tests/factory/test_dry_run_parity.py` and per-command tests |
| Error messages | Same text and same `Hint:` (when present) | per-command tests (`strip_ansi`), `tests/commands/test_behavior_contract.py` |
| Exit codes | `0` success or help, `1` user error, `2` `uv` failure in `up` | per-command tests |
| `pyproject.toml` | Same injected dependencies, groups and `[project.scripts]` | `tests/core/test_pyproject_writer.py` and gep/gda tests |

## Allowed changes (exhaustive)

### C-1: unified project context (FR-010)

- **Before**: `gep` and `gep --add-tool` used `to_snake_case([project].name)`, with `"project"` as the default.
- **After**: every command uses `[tool.scaffold-ca-python].name`, falling back to the root directory name.
- **Impact**: it only changes for projects where `[project].name` was edited by hand and no longer matches the tool section.

### C-2: `gpipe` conflict message (FR-016)

- **Before**:
  ```
  Error: '<display>' already exists at '<path>'. Use --force to overwrite.
  Hint: Remove the existing file first or choose a different provider.
  ```
- **After**:
  ```
  Error: '<display>' already exists at '<path>'.
  Hint: Remove the existing file first or choose a different provider.
  ```

### C-3: TOML sections visible in the `gep` output (FR-021)

- **Before**: Rich interprets `[project.scripts]` as markup and drops it:
  ```
  Would update : my_app = "my_app.server:start_server"
  ✓ Updated : my_app = "my_app.server:start_server"
  ```
- **After**: `escape()` is applied, as is already done for `[project.dependencies]`:
  ```
  Would update [project.scripts]: my_app = "my_app.server:start_server"
  ✓ Updated [project.scripts]: my_app = "my_app.server:start_server"
  ```
