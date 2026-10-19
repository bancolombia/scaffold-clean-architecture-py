---

description: "Task list for 021-mcp-add-tool"
---

# Tasks: Incremental MCP Tool Addition

**Input**: Design documents from `/specs/021-mcp-add-tool/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/gep-add-tool.md, quickstart.md

**Tests**: Included and sequenced before their implementation tasks — Constitution Principle V ("Test-First Development (NON-NEGOTIABLE)") mandates Red-Green-Refactor for this project, so test tasks are not optional here.

**Organization**: Tasks are grouped by user story (from `spec.md`) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths are included in every description

## Path Conventions

Single-project CLI layout (per `plan.md` Project Structure — no frontend/backend or mobile split applies):
- CLI source: `src/scaffold_ca_python/`
- Templates: `src/scaffold_ca_python/templates/`
- Tests: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the placeholder files and shared test fixture every later phase builds on

- [x] T001 [P] Create empty placeholder template files `src/scaffold_ca_python/templates/entry_point/mcp/tool_stub.py.jinja2` and `src/scaffold_ca_python/templates/entry_point/mcp/test_tool_stub.py.jinja2` (content added in Phase 2)
- [x] T002 [P] Create empty module file `src/scaffold_ca_python/core/mcp_tool_spec.py` with a module docstring only (implementation added in Phase 2)
- [x] T003 [P] Create new test module `tests/core/test_mcp_tool_spec.py` with imports only (tests added in Phase 2)
- [x] T004 [P] Add a shared `mcp_project` pytest fixture to `tests/commands/test_generate_entry_point.py` that bootstraps a project via `runner.invoke(app, ["ca", "--name", "my-app"])` then `runner.invoke(app, ["gep", "--type", "mcp"])`, for reuse by all `--add-tool` tests in later phases

**Checkpoint**: Placeholder files exist; nothing behavioral yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented — a regression guard confirming `tools.py.jinja2` stays unchanged, the two new stub templates, the new `AppendToFile` file-operation primitive, the `mcp_tool_spec` validation module, and the new CLI flags

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 **[Regression guard — not a Red-Green cycle]** Add a rendering test in `tests/templates/test_entry_point_templates.py` asserting that rendering `entry_point/mcp/tools.py.jinja2` (which this feature does NOT modify) parses with `ast`, that its last top-level statement is `async def bind_tools`, and that `bind_tools` contains the nested `@mcp.tool("example_tool")` function. This test passes immediately against the current template; its purpose is to fail if a future change breaks the insertion-point invariant `--add-tool` relies on. Confirm the pre-existing `example_tool` rendering/registration tests still pass unchanged
- [x] T008 Write failing rendering tests in `tests/templates/test_entry_point_templates.py` for the two new templates: for `entry_point/mcp/tool_stub.py.jinja2`, render with a sample context (`name`, `params: list[{name, type}]`, `returns`, `docstring`) and assert the output contains a **4-space-indented** nested `@mcp.tool("<name>")`-decorated `async def <name>(...)` signature with the params in order and the given return type, the docstring, and `raise NotImplementedError(...)` — **NOT** wrapped in `@_register_tool` or `def _bind_<name>`; for `entry_point/mcp/test_tool_stub.py.jinja2`, assert the output contains a top-level `test_bind_tools_registers_<name>` function and an `assert "<name>" in registered` line, and does NOT call/await the registered tool itself; confirm both tests FAIL (templates are still empty from T001)
- [x] T009 [P] Implement `src/scaffold_ca_python/templates/entry_point/mcp/tool_stub.py.jinja2` to render a **4-space-indented** inline nested function block preceded by exactly **one** blank line (it lands inside `bind_tools`, where `ruff format` allows only single blank lines, matching the base template's spacing before `example_tool`): `\n    @mcp.tool("{{ name }}")\n    async def {{ name }}({% for param in params %}{{ param.name }}: {{ param.type }}{% if not loop.last %}, {% endif %}{% endfor %}) -> {{ returns }}:\n        """{{ docstring }}"""\n        raise NotImplementedError("Tool '{{ name }}' is not yet implemented.")` (nested function format for appending inside `bind_tools`, not a top-level registrar); confirm the matching half of T008 now PASSES
- [x] T010 [P] Implement `src/scaffold_ca_python/templates/entry_point/mcp/test_tool_stub.py.jinja2` to render a top-level `test_bind_tools_registers_{{ name }}` function using the existing `_make_mock_mcp()` helper pattern already present in `test_tools.py.jinja2`, asserting registration only; confirm the matching half of T008 now PASSES
- [x] T011 [P] Write failing unit tests in `tests/core/test_mcp_tool_spec.py` covering: `parse_param` (accepts `"path:str"` → `("path", "str")` and the soft keyword `"match:str"`; rejects `"path"` with no colon, `"Path:str"` bad casing, `"class:str"` hard keyword with an error naming the keyword, `"path:print('x')"` bad type); `validate_type_expression` (accepts `str`, `int`, `list[str]`, `dict[str, int]`, `str | None`, `typing.Optional[str]`, `Literal["a", "b"]`; rejects `print('x')`, a bare string literal `"hello"`, `1 + 1`, a lambda, and a comprehension — per the grammar in `research.md` R-004); `find_existing_tool_names` (parses a `tools.py`-shaped source string and returns the union of every `@<x>.tool("name")` registered name, the name of every function defined directly inside `bind_tools`, and the reserved name `bind_tools` — per FR-010 and the spec's reserved-name edge case; includes a case where `@mcp.tool("search")` decorates `async def do_search`, asserting both `search` and `do_search` are returned; ignores tool-name-like text inside comments/docstrings); `has_bind_tools_function` (returns `True` only when the **last top-level statement** of `tools.py`'s source is an `async def bind_tools`, via `ast`; `False` when the function is absent, not async, only present inside a comment/string, followed by another top-level function, or followed by a top-level assignment such as `__all__ = [...]`); `has_test_registration_structure` (returns `True` only when `test_tools.py`'s source defines a top-level `_make_mock_mcp` function and imports both `bind_tools` and `asyncio`; `False` when any of the three is missing); `validate_description` (accepts normal text, returns the generic placeholder for `None`/empty input, rejects text containing an embedded `"""` or `'''`); and `build_tool_spec`/`ToolSpec`/`ParamSpec` (rejects `--name class` / `--name import` per FR-003's keyword rule while accepting `--name match`; rejects duplicate `--param` names per FR-006, applies the `"str"` return-type default and the placeholder-docstring default, preserves `--param` order); confirm all tests FAIL
- [x] T012 Implement `ParamSpec`, `ToolSpec`, `parse_param`, `validate_type_expression`, `find_existing_tool_names`, `has_bind_tools_function`, `has_test_registration_structure`, `validate_description`, `build_tool_spec` in `src/scaffold_ca_python/core/mcp_tool_spec.py`, reusing `core.name_utils.validate_module_name` for name checks plus the stdlib `keyword.iskeyword` for the hard-keyword rejection (FR-003/FR-005; soft keywords are not rejected), and the stdlib `ast` module for `validate_type_expression`/`find_existing_tool_names`/`has_bind_tools_function`/`has_test_registration_structure` per `research.md` R-003–R-005, R-007 and `data-model.md` "Insertion Point"; implement `ParamSpec` and `ToolSpec` as Pydantic v2 `BaseModel` subclasses (not plain dataclasses) per `data-model.md`, consistent with `ModuleContext`/`ProjectContext` and Constitution Principle II's "Template context objects MUST be validated via Pydantic models before rendering," with a model validator on `ToolSpec` rejecting duplicate `--param` names (FR-006); confirm all of T011 now PASSES
- [x] T013 [P] Write failing unit tests in `tests/core/test_file_writer.py` for a new `AppendToFile` operation and `FileWriter._apply_append_to_file`: appending to an existing file first normalizes the file's trailing blank lines to a single newline, then appends `content` verbatim (so the blank-line spacing comes from `content` itself, per `data-model.md`), without disturbing earlier content; targeting a file that does **not** exist creates it (including any missing parent directories) with `content` as its initial contents; dry-run mode returns the target path without writing to disk, matching `InsertAfter`'s existing dry-run contract. Also write failing tests in `tests/factory/test_module_builder.py` for `ModuleBuilder.append_to_file(path, content)`: it queues exactly one `AppendToFile` with the given path and content, and `persist()` applies it to disk (and, with `dry_run=True`, returns the path without writing). Confirm all tests FAIL (per `research.md` R-006; Constitution Principle V)
- [x] T014 Implement the new `AppendToFile` `FileOperation` model in `src/scaffold_ca_python/models/file_operation.py` (alongside, not replacing, `CreateFile`/`DeleteFile`/`InsertAfter`), `FileWriter._apply_append_to_file` in `src/scaffold_ca_python/core/file_writer.py`, and `ModuleBuilder.append_to_file(path, content)` in `src/scaffold_ca_python/core/module_builder.py` (mirroring the existing `insert_after` method's signature style, without modifying `insert_after`/`_apply_insert_after`/`InsertAfter` in any way); confirm all of T013 (both `tests/core/test_file_writer.py` and `tests/factory/test_module_builder.py`) now PASSES and all pre-existing `insert_after`/`InsertAfter` tests still pass unchanged
- [x] T015 [P] Add `--add-tool` (bool flag, default `False`), `--name` (str, default `None`), `--param` (repeatable `Annotated[list[str] | None, typer.Option("--param")]`, default `None`), `--returns` (str, default `"str"`), and `--description` (str, default `None`) Typer options to the `generate_entry_point`/`gep` command signature in `src/scaffold_ca_python/commands/generate_entry_point.py`, threading all five through to `_generate_entry_point_impl` (flag wiring only — no new behavior yet; existing flags/behavior unchanged)
- [x] T016 Add the `--add-tool` dispatch in `src/scaffold_ca_python/commands/generate_entry_point.py`: (a) in the `generate_entry_point` command function, **before** the existing `if type_ is None: … print help … raise typer.Exit(0)` shortcut, when `add_tool` is `True` and `type_` is `None`, print the FR-012 message (contract rule 1) and `raise typer.Exit(code=1)` — otherwise `gep --add-tool --name x` would silently show help and exit `0`; (b) at the top of `_generate_entry_point_impl`, when `add_tool` is `True`, call a new `_add_tool_impl(type_, swagger, enable_kafka, enable_mcp_client, with_resources, with_prompts, name, param, returns, description, dry_run)` — passing every creation-only flag so T028 can reject them (FR-011) — initially a minimal stub (e.g. `raise typer.Exit(code=1)` with a `TODO` placeholder message), instead of running the existing creation-path logic, per `research.md` R-002; confirm the existing (no-flag) `gep --type mcp` creation tests and the existing no-`--type` help behavior (without `--add-tool`) still pass unchanged

**Checkpoint**: The `AppendToFile` primitive exists and is unit-tested, `tools.py.jinja2` is unchanged and guarded by a regression test, the two new stub templates render correctly with 4-space indentation and are unit-tested, `mcp_tool_spec.py` is fully implemented and unit-tested with `has_bind_tools_function` and `has_test_registration_structure`, and the CLI accepts all five new flags and routes `--add-tool` invocations to a (currently empty) `_add_tool_impl`. User story implementation can now begin.

---

## Phase 3: User Story 1 - Add a new tool to an existing MCP server (Priority: P1) 🎯 MVP

**Goal**: `scaffold gep --type mcp --add-tool --name ... [--param ...] [--returns ...] [--description ...]` appends exactly one working, correctly-typed tool stub to `tools.py` and a matching registration test to `test_tools.py`, leaving all previously existing tools untouched.

**Independent Test**: Bootstrap a project with `scaffold gep --type mcp`, then run the full-flag `--add-tool` invocation from the spec's example and verify the new tool appears correctly in `tools.py`, is registered per the new `test_tools.py` assertion, and all previously existing tools/tests are unchanged.

### Tests for User Story 1 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle V)

> **Note (append-or-create scope)**: `ModuleBuilder.append_to_file`/`AppendToFile` generically supports creating a target file from scratch when it does not yet exist (T013/T014). In this feature's actual usage, `test_tools.py` is always already present (created by the base `gep --type mcp` path before `--add-tool` can run at all per FR-009's entry-point-exists guard), so the create-from-scratch branch is exercised only by `AppendToFile`'s own unit tests (T013), never by an end-to-end `--add-tool` CLI test — this is intentional and does not need additional `--add-tool`-level coverage.

- [x] T017 [US1] Write failing CLI tests in `tests/commands/test_generate_entry_point.py` (using the `mcp_project` fixture from T004) for the US1 happy-path acceptance scenarios: (1) full-flag invocation (`--name create_file --param path:str --param content:str --returns str --description "Creates a file on disk"`) inserts a correctly-shaped `create_file` stub into `tools.py` with the given params/return type/docstring and exit code `0`; (2) zero `--param` flags produce a stub that takes no extra parameters beyond the tool-binding mechanism's own; (3) omitted `--returns`/`--description` default the stub to a `str` return type and a generic, clearly-marked placeholder docstring; (4) the pre-existing `example_tool` and its tests remain present and unchanged after the run; (5) `test_tools.py` gains a `test_bind_tools_registers_create_file` assertion and the full `test_tools.py` file (as a standalone pytest run against the generated project) passes, including the new assertion; (6) a full `pathlib.Path.rglob("*")` snapshot of the project tree taken before and after the run shows exactly `tools.py` and `test_tools.py` changed — no domain model, use case, gateway, or driven-adapter file is created, modified, or deleted (FR-014); confirm all FAIL

### Implementation for User Story 1

> **Guard ordering note** (aligned with `research.md` R-002 and `contracts/gep-add-tool.md`'s "evaluated in order, first failure wins" guard-rule list): all *format/content* validation of `--name`/`--param`/`--returns`/`--description` (FR-002, FR-003, FR-005, FR-006, FR-007, FR-008) MUST complete — with zero filesystem/project access — before any check that depends on project state (FR-009 entry-point-exists, FR-017 `bind_tools`-presence and test-file structure, FR-010 duplicate-tool-name, FR-019 writability). This corrects an earlier draft of this task list that checked project state first; T018–T020 below reflect the corrected order.

- [x] T018 [US1] In `_add_tool_impl` (`src/scaffold_ca_python/commands/generate_entry_point.py`), implement the format-only guard sequence — no project/filesystem access yet: fail with an actionable error if `name` is `None` (FR-002); otherwise build the fully validated `ToolSpec` via `mcp_tool_spec.build_tool_spec(name, param, returns, description)`, which performs `--name`/`--param`-name snake_case validation (FR-003), `--param` format/type validation (FR-005), duplicate-`--param`-name rejection (FR-006), `--returns` type validation (FR-007), and `--description` docstring-safety validation (FR-008) (depends on T012, T016)
- [x] T019 [US1] In `_add_tool_impl`, only after T018's `ToolSpec` is built successfully, resolve `project_root`/`project_ctx` via the existing `find_project_root`/`_load_project_context` helpers, then fail with an actionable error (hinting at `scaffold gep --type mcp`) if `infrastructure/entry_points/mcp_server/tools.py` does not exist (FR-009) (depends on T018)
- [x] T020 [US1] In `_add_tool_impl`, implement the bind_tools-function-presence guard (FR-017, via `mcp_tool_spec.has_bind_tools_function` on the current `tools.py` source), then the test-file structure guard (FR-017, contract rule 10b: `test_tools.py` missing/unreadable or `mcp_tool_spec.has_test_registration_structure` returns `False`), both **strictly before** the duplicate-tool-name guard (FR-010, via `mcp_tool_spec.find_existing_tool_names` on the current `tools.py` source), per `contracts/gep-add-tool.md`'s ordered guard-rule list (rule 10 — legacy/bind_tools-missing — precedes rule 11 — duplicate name); a project missing its `async def bind_tools` function MUST fail with the FR-017 regeneration-hint message even if it would also match an FR-010 duplicate-name condition; read both files directly with `Path.read_text()` before any builder operation is queued, and keep both original texts for T030a's restore-on-failure (depends on T012, T019)
- [x] T021 [US1] In `_add_tool_impl`, render `tool_stub.py.jinja2` and `test_tool_stub.py.jinja2` via `builder.render(...)` using the `ToolSpec` context, as a safety net run `ast.parse(original_tools_py + rendered_inline_block)` and raise the FR-017 regeneration error if it fails (so an unparseable `tools.py` is never written), then queue `builder.append_to_file(tools_py_path, content=<rendered_inline_block>)` (the 4-space-indented nested function) and `builder.append_to_file(test_tools_py_path, content=<rendered test>)`, call `builder.persist()`, and print a `[green]✓[/green]` success message naming the new tool; the inline block appended to the end of `tools.py` effectively inserts the new tool inside `bind_tools` since `bind_tools` is always the last function (depends on T009, T010, T014, T020); confirm all of T017 now PASSES

**Checkpoint**: User Story 1 is fully functional and independently testable — run `uv run pytest tests/commands/test_generate_entry_point.py -k add_tool` to verify in isolation.

---

## Phase 4: User Story 2 - Clear guardrails prevent invalid or conflicting requests (Priority: P2)

**Goal**: Every misuse of `--add-tool` — missing entry point, duplicate name, incompatible flags, invalid `--name`/`--param`/`--returns`/`--description`, a legacy project without `bind_tools` as its last top-level statement, a missing/unrecognized `test_tools.py`, or an unwritable target file — fails immediately with an actionable message and exit code `1`, never a crash or a partial file write.

**Independent Test**: Run each guard-rail scenario from `spec.md` User Story 2 against appropriately set-up fixtures and verify the exact failure behavior (message, exit code, no file changes) independently of whether US1's happy path has been exercised in the same test run.

### Tests for User Story 2 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle V)

- [x] T022 [US2] Write failing CLI tests in `tests/commands/test_generate_entry_point.py` for: the entry-point-does-not-exist guard (FR-009, scenario 1 — project bootstrapped with `ca` only, no `gep --type mcp` run) asserting the hint to run `scaffold gep --type mcp` first; and the duplicate-tool-name guard (FR-010, scenario 2), parametrized over: `--add-tool --name create_file` run twice; a hand-edited `tools.py` where `@mcp.tool("search")` decorates `async def do_search`, rejecting both `--name search` and `--name do_search`; and the reserved `--name bind_tools` (asserting the reserved-name variant of contract rule 11, not the "already exists" wording) — each asserting the run fails and `tools.py` is unchanged; all asserting exit code `1`
- [x] T023 [US2] Write failing CLI tests, parametrized, for the flag/type incompatibility guards: `--add-tool` combined with each of `--swagger`, `--enable-kafka`, `--enable-mcp-client`, `--with-resources`, `--with-prompts` fails naming the offending flag (FR-011, scenario 3); `--add-tool` combined with `--type restapi`/`--type agent`/`--type generic`, and with `--type` omitted entirely, fails stating `--add-tool` requires `--type mcp` (FR-012, scenario 4); all asserting exit code `1` and no file changes
- [x] T024 [US2] Write failing CLI tests, parametrized, for the required/format validation guards: `--add-tool` with no `--name` (FR-002, scenario 5); `--name CreateFile` bad casing (FR-003, scenario 6, same error style as `generate-model`'s `validate_module_name` error); `--name class` and `--param class:str` hard keywords (FR-003/FR-005, contract rules 4/5 keyword variants, each naming the keyword) while `--name match` is accepted; malformed `--param` values `"path"` (no colon), `"Path:str"` (bad param-name casing), and `"path:print('x')"` (non-type-expression) each identifying the offending value (FR-005, scenario 7); duplicate `--param` names `--param path:str --param path:int` (FR-006); and a non-type-expression `--returns "print('x')"` (FR-007, scenario 8); all asserting exit code `1` and no file changes
- [x] T025 [US2] Write failing CLI tests for: an unsafe `--description` containing an embedded `"""` sequence (FR-008); a "legacy" project simulated by removing or renaming the `async def bind_tools` function from an otherwise-valid generated `tools.py` (FR-017, scenario 9) asserting a regeneration-hint message and **not** a raw `ValueError`/`FileNotFoundError` traceback, **and** asserting `tools.py`/`test_tools.py` content is byte-identical to its pre-attempt state afterward (SC-005 — zero file corruption); a "hand-edited" `tools.py` where a top-level `def helper()` follows `bind_tools` (FR-017, `bind_tools` not last) asserting the regeneration-hint message and byte-identical files; a missing/unreadable `tools.py` (entry-point directory present, file absent) asserting a clear message rather than a crash; and, for US2 scenario 10, a missing `test_tools.py` and a `test_tools.py` with `_make_mock_mcp` removed, each asserting the contract rule 10b message and that `tools.py` is byte-identical afterward; all asserting exit code `1`
- [x] T025a [US2] Write failing CLI tests for FR-019: (a) `test_tools.py` made read-only via `chmod 0o444` — the command fails with the contract rule 12 message before any write, and `tools.py` is byte-identical afterward (mark `skipif` on Windows or when running as root, where the permission bit is not enforced); (b) `FileWriter._apply_append_to_file` monkeypatched to raise `OSError` on its second call — the command exits `1` with the contract rule 13 message and both `tools.py` and `test_tools.py` are byte-identical to their pre-attempt state
- [x] T026 [US2] Write failing CLI tests for two cross-cutting guard-ordering scenarios required by `contracts/gep-add-tool.md`'s "evaluated in order, first failure wins" rule: (1) invoke `--add-tool` with an invalid `--param` (e.g. `--param "path:print('x')"`, FR-005) against a project that has **no** MCP entry point generated yet (FR-009 would also apply); assert the failure message identifies the invalid `--param` (FR-005 wording), not the missing-entry-point message (FR-009); (2) invoke `--add-tool --name create_file` against a project whose `tools.py` already defines `create_file` (would match FR-010) **and** whose `async def bind_tools` function has been removed (would match FR-017); assert the failure message is the FR-017 regeneration-hint message, not the FR-010 duplicate-name message, per guard rule 10 preceding rule 11 in `contracts/gep-add-tool.md`; both asserting exit code `1`; these tests MUST fail against the pre-reorder guard sequence and MUST pass once T018–T020's corrected order is implemented

### Implementation for User Story 2

- [x] T027 [US2] Wire the entry-point-existence (FR-009) and duplicate-tool-name (FR-010) guard messages in `_add_tool_impl` to match `contracts/gep-add-tool.md`'s guard-rule wording exactly (depends on T019, T020); confirm T022 now PASSES
- [x] T028 [US2] Wire the flag/type incompatibility guard messages (FR-011, FR-012) in `_add_tool_impl` using the creation-only flags T016 passes in (the `--type`-omitted case is already handled in the command function by T016(a)), ensuring these checks run before project-root resolution so no project lookup is attempted on an invalid flag combination (depends on T016); confirm T023 now PASSES
- [x] T029 [US2] Surface `mcp_tool_spec` validation errors — from `parse_param`, `validate_type_expression` (for both `--param` types and `--returns`), and the duplicate-`--param`-name check — as `[red]Error:[/red]` CLI messages quoting the offending value, in `_add_tool_impl` (depends on T012, T018); confirm T024 now PASSES
- [x] T030 [US2] Wire the `--description` safety guard (via `mcp_tool_spec.validate_description`, already enforced as part of T018's `build_tool_spec` call), the bind_tools-function-presence guard message (FR-017, from T020), the test-file structure guard message (contract rule 10b, from T020), and the missing/unreadable-`tools.py` guard in `_add_tool_impl` to match `contracts/gep-add-tool.md`'s regeneration-hint wording, ensuring no partial file write occurs before any of these checks (depends on T012, T018, T020); confirm T025 now PASSES; confirm T026 now PASSES (verifies the corrected guard order from T018–T020)
- [x] T030a [US2] Implement FR-019 in `_add_tool_impl` (`src/scaffold_ca_python/commands/generate_entry_point.py`): after the duplicate-name guard and before queuing any operation, check `os.access(path, os.W_OK)` for both `tools.py` and `test_tools.py`, failing with the contract rule 12 message if either is not writable; wrap `builder.persist()` in `try/except OSError`, and on failure write both original texts (kept by T020) back with `Path.write_text()`, print the contract rule 13 message, and exit `1` (depends on T020, T021); confirm T025a now PASSES

**Checkpoint**: User Stories 1 AND 2 both work independently — every invalid/conflicting invocation fails safely and the US1 happy path is unaffected.

---

## Phase 5: User Story 3 - Preview the change before writing it (Priority: P3)

**Goal**: `--add-tool --dry-run` previews the exact file(s) and code snippet that would be inserted, without writing to disk, and matches what an equivalent live run actually produces.

**Independent Test**: Run the same `--add-tool` invocation once with `--dry-run` and once without, and confirm the preview output matches the real result while the dry run itself leaves disk contents unchanged.

### Tests for User Story 3 ⚠️

> Write these tests FIRST, ensure they FAIL before implementation (Constitution Principle V)

- [x] T031 [US3] Write failing CLI tests in `tests/commands/test_generate_entry_point.py` for: `--add-tool --dry-run` with a valid invocation printing the files that would change (`tools.py`, `test_tools.py`) and the exact stub/test snippet, while `tools.py`/`test_tools.py` remain byte-for-byte unchanged on disk and exit code is `0` (scenario 1); re-running the identical invocation immediately afterward without `--dry-run` produces file contents identical to what the dry run printed (scenario 2); and `--add-tool --dry-run` against a project with no MCP entry point still fails with the FR-009 message instead of showing any preview (edge case — missing-entry-point guard takes precedence)

### Implementation for User Story 3

- [x] T032 [US3] In `_add_tool_impl`, when `dry_run` is `True`, print the already-rendered stub/test snippets (via `rich.syntax.Syntax`) alongside the list of files that would be modified, and return before calling `builder.persist()` with any real write; ensure every guard from T018/T019/T020/T027/T028/T030/T030a (except the persist-time restore, which only applies to real writes) still runs (and can still fail) before this preview output, per `research.md` R-008 (depends on T021); confirm T031 now PASSES

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, held-out validation, and quality gates spanning all three user stories

- [x] T033 [P] Update the `scaffold gep` section of `README.md` with a concrete `--add-tool` usage example (mirroring the existing `--with-resources --with-prompts --dry-run` example already documented there)
- [x] T034 [P] Update `_GEP_EPILOG` in `src/scaffold_ca_python/commands/generate_entry_point.py` with a concrete `--add-tool` usage example, per Constitution Principle VI ("`--help` output for every command MUST include at least one concrete usage example")
- [x] T035 Run the `specs/021-mcp-add-tool/quickstart.md` validation script end-to-end against a freshly scaffolded project and fix any discrepancy found between the guide and actual behavior
- [x] T036 Run `uv run pytest --cov=scaffold_ca_python --cov-report=term-missing` and confirm the 80% line-coverage gate still passes (Constitution Principle V)
- [x] T037 [P] Run `ruff check` and `mypy --strict` over all new/modified files (`generate_entry_point.py`, `mcp_tool_spec.py`, `module_builder.py`, `file_writer.py`, `models/file_operation.py`, the two new Jinja2 templates, and all new/modified test files) and fix any violations (Constitution Principle IV)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion (T001–T004) — BLOCKS all user stories
- **User Stories (Phase 3–5)**: All depend on Foundational phase (T005, T008–T016) completion
  - User Story 1 (T017–T021) can start immediately after Foundational
  - User Story 2 (T022–T030a) builds on the guard-sequence skeleton US1 establishes (T018, T019, T020) — implement after US1 for a smooth increment, though its tests (T022–T026, T025a) only require Foundational + the guard skeleton to exist
  - User Story 3 (T031–T032) builds on the render/append path US1 establishes (T021) — implement after US1
- **Polish (Phase 6)**: Depends on all three user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) — no dependency on US2/US3
- **User Story 2 (P2)**: Technically exercises guard code introduced in US1 (T018, T019, T020); its own tests (T022–T026, T025a) are independent and could be written in parallel with US1, but its implementation tasks (T027–T030a) assume T018/T019/T020 exist (and T030a also assumes T021)
- **User Story 3 (P3)**: Exercises the render/append path from US1 (T021); its tests (T031) are independent, but its implementation (T032) assumes T021 exists

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Constitution Principle V)
- All implementation tasks within `_add_tool_impl` for a given story are sequential (same function, same file) — no `[P]` within a story's implementation block

### Parallel Opportunities

- Setup: T001, T002, T003, T004 can all run in parallel (four independent files)
- Foundational: T009 ∥ T010 (different template files); T011 can run parallel to the template-track tasks (T005, T008–T010, different file); T013 can run parallel to the template-track and `mcp_tool_spec` tracks (different file); T015 can run parallel to the template-track, `AppendToFile`, and `mcp_tool_spec` tracks (different file)
- Polish: T033 ∥ T034 ∥ T037 (different files/concerns)
- Across phases: once Foundational (T005, T008–T016) is complete, the test-writing tasks for US2 (T022–T026, T025a) and US3 (T031) can be drafted in parallel with US1's implementation (T018–T021) by a different contributor, since they target the same test file but different scenarios — coordinate to avoid merge conflicts, or sequence them as listed

---

## Parallel Example: Foundational Phase

```bash
# Regression guard (passes immediately; tools.py.jinja2 is unchanged):
Task: "Add bind_tools-is-last rendering guard test"    # T005

# After T008 (failing stub-template tests) is committed:
Task: "Implement tool_stub.py.jinja2"                  # T009
Task: "Implement test_tool_stub.py.jinja2"             # T010

# Independently of the template track above:
Task: "Write mcp_tool_spec.py unit tests"              # T011

# Independently of both tracks above (new AppendToFile primitive):
Task: "Write AppendToFile/_apply_append_to_file unit tests"  # T013

# Independently of all tracks above:
Task: "Add --add-tool CLI flags to generate_entry_point.py"  # T015
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T004)
2. Complete Phase 2: Foundational (T005, T008–T016) — CRITICAL, blocks all stories
3. Complete Phase 3: User Story 1 (T017–T021)
4. **STOP and VALIDATE**: Run `uv run pytest tests/commands/test_generate_entry_point.py -k add_tool` and the relevant steps of `quickstart.md` (sections 1–3) to confirm the happy path works end-to-end
5. This is already a usable MVP: developers can add tools, just without hardened guard rails or dry-run support yet

### Incremental Delivery

1. Setup + Foundational → foundation ready (`bind_tools` regression guard, stub templates, `AppendToFile` primitive, validators, CLI flags all in place)
2. Add User Story 1 → test independently → MVP: `--add-tool` works for valid input
3. Add User Story 2 → test independently → every invalid/conflicting invocation now fails safely, and write failures leave no partial changes
4. Add User Story 3 → test independently → `--dry-run` preview available
5. Polish → docs, quickstart validation, coverage gate, lint/type-check
