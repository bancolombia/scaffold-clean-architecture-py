# Quickstart: Validating `gep --type mcp --add-tool`

**Feature**: `021-mcp-add-tool`
**Audience**: Developer implementing or reviewing this feature

---

## Prerequisites

- Python ≥3.13 with [uv](https://docs.astral.sh/uv/) installed
- This repository checked out on `feature/021-mcp-add-tool`
- `uv sync` run at least once (installs `scaffold-ca-python` in editable mode plus dev/test deps)

---

## 1. Scaffold a throwaway project and a base MCP entry point

```bash
cd /tmp
uv run --project /path/to/scaffold-clean-architecture-py scaffold ca --name demo-mcp
cd demo-mcp
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp
```

Expected: `src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py` and `tests/infrastructure/entry_points/mcp_server/test_tools.py` exist, each containing the `example_tool` stub — `tools.py` defines `example_tool` nested inside `async def bind_tools`, which is the last top-level statement in the file (see `data-model.md` "Insertion Point").

---

## 2. Preview adding a tool with `--dry-run`

```bash
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool \
  --name create_file --param path:str --param content:str --returns str \
  --description "Creates a file on disk" --dry-run
```

Expected (per `contracts/gep-add-tool.md`):
- Output names `tools.py` and `test_tools.py` as the files that would change.
- Output shows the exact `create_file` stub snippet (see contract's "Generated Snippet" section).
- `tools.py` and `test_tools.py` are byte-for-byte unchanged on disk afterward.
- Exit code `0`.

---

## 3. Add the tool for real

```bash
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool \
  --name create_file --param path:str --param content:str --returns str \
  --description "Creates a file on disk"
```

Expected:
- `tools.py` now contains an additional `@mcp.tool("create_file")` async function, matching the dry-run preview exactly.
- `test_tools.py` now contains an additional `test_bind_tools_registers_create_file` test.
- The pre-existing `example_tool` stub and its tests are untouched.
- Exit code `0`.

Verify with pytest from inside `demo-mcp`:

```bash
uv run pytest tests/infrastructure/entry_points/mcp_server/test_tools.py -v
```

Expected: all tests pass, including the newly added `test_bind_tools_registers_create_file` (it only asserts registration — it must NOT call the stub, since the stub body raises `NotImplementedError`).

---

## 4. Exercise the guard rails

Each of these MUST fail with an actionable message and a non-zero exit code, and MUST NOT modify any file (verify with `git status` / `git diff` inside `demo-mcp` if it's a git repo, or re-run step 2's dry-run diff check):

```bash
# Duplicate tool name (FR-010)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name create_file

# Missing --name (FR-002)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool

# Invalid --name casing (FR-003)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name CreateFile

# Python keyword as --name or --param name (FR-003 / FR-005)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name class
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --param class:str

# Reserved tool name (FR-010)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name bind_tools

# --add-tool without --type (FR-012) — must fail with exit 1, not print help
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --add-tool --name read_file

# Malformed --param (FR-005)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --param path

# Non-type-expression --param type (FR-005 / research.md R-004)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --param "path:print('x')"

# Duplicate --param names (FR-006)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --param path:str --param path:int

# Non-type-expression --returns (FR-007)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --returns "print('x')"

# Docstring-breaking --description (FR-008)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --description 'breaks """ here'

# Incompatible flag combination (FR-011)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name read_file --with-resources

# Wrong --type (FR-012)
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type restapi --add-tool --name read_file
```

---

## 5. Exercise the "entry point doesn't exist yet" guard (FR-009)

```bash
cd /tmp
uv run --project /path/to/scaffold-clean-architecture-py scaffold ca --name demo-no-mcp
cd demo-no-mcp
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name create_file
```

Expected: fails with a message explaining the MCP entry point doesn't exist yet and a hint to run `scaffold gep --type mcp` first. Exit code `1`.

---

## 6. Exercise the "legacy project / missing `bind_tools`" guard (FR-017)

```bash
cd demo-mcp   # from step 1 — already has an entry point
cp src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py /tmp/tools.py.bak
# Simulate a pre-feature project by renaming bind_tools
sed -i '' 's/async def bind_tools/async def bind_tools_legacy/' src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name another_tool
```

Expected: fails with a clear message recommending regeneration of the entry point — **not** a raw `ValueError`/`FileNotFoundError` traceback. Exit code `1`.

Then simulate a hand-edited file where `bind_tools` is no longer last:

```bash
cp /tmp/tools.py.bak src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py
printf '\n\ndef helper() -> None:\n    pass\n' >> src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name another_tool
cp /tmp/tools.py.bak src/demo_mcp/infrastructure/entry_points/mcp_server/tools.py
```

Expected: the same FR-017 failure (hint mentions making `bind_tools` the last function), and `tools.py` is unchanged by the command. Exit code `1`.

## 6b. Exercise the missing-test-file guard (FR-017)

```bash
mv tests/infrastructure/entry_points/mcp_server/test_tools.py /tmp/test_tools.py.bak
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --add-tool --name another_tool
mv /tmp/test_tools.py.bak tests/infrastructure/entry_points/mcp_server/test_tools.py
```

Expected: fails with the guard 10b message from `contracts/gep-add-tool.md`; `tools.py` is unchanged. Exit code `1`.

---

## 7. Run the project's own test suite

From the `scaffold-clean-architecture-py` repository root:

```bash
uv run pytest tests/commands/test_generate_entry_point.py tests/core/test_mcp_tool_spec.py \
  tests/templates/test_entry_point_templates.py tests/factory/entry_points/test_ep_mcp.py -v
```

Expected: all tests pass, including the new `--add-tool` success/guard tests and the two new template rendering tests, with no regressions in the pre-existing `gep --type mcp` creation tests.

```bash
uv run pytest --cov=scaffold_ca_python --cov-report=term-missing
```

Expected: coverage gate (≥80% per Constitution Principle V) still passes.

---

## Cleanup

```bash
rm -rf /tmp/demo-mcp /tmp/demo-no-mcp
```
