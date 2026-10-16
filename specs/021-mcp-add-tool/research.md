# Research: Incremental MCP Tool Addition

**Date**: 2026-10-15
**Feature**: `021-mcp-add-tool`

---

## R-001: Flag design and CLI wiring

**Decision**: Add `--add-tool` (bool flag), `--name` (str, optional at the Typer level but required when `--add-tool` is set), `--param` (repeatable `list[str]`, zero or more), `--returns` (str, default `"str"`), and `--description` (str, optional) directly onto the existing `generate_entry_point` / `gep` Typer command, alongside the current `--type`, `--swagger`, `--enable-kafka`, `--enable-mcp-client`, `--with-resources`, `--with-prompts`, `--dry-run` options. `--param` uses Typer's native support for `Annotated[list[str] | None, typer.Option("--param")]`, which Click/Typer already collects into a list across repeated invocations with no extra wiring.

**Rationale**: The user's requirement explicitly frames `--add-tool` as a flag *on* `gep`, not a new subcommand (`scaffold gep --type mcp --add-tool ...`). Keeping it on the same Typer command avoids duplicating the project-root resolution, project-context loading, and flag-compatibility-guard code that already lives in `_generate_entry_point_impl`.

**Alternatives considered**: A separate `scaffold add-tool` command. Rejected — contradicts the explicit requirement and would duplicate `_load_project_context`/`find_project_root`/flag-guard logic that `generate_entry_point.py` already owns.

---

## R-002: Control-flow branching for the inverse guard

**Decision**: At the top of `_generate_entry_point_impl`, branch early when `add_tool` is `True`: run a dedicated `_add_tool_impl(...)` path that performs its own guard sequence (flag-compatibility → name/param/returns/description validation → project resolution → **entry point MUST exist** guard → `bind_tools`-presence guard → test-file-structure guard → duplicate-tool guard → writability pre-check → render → append_to_file → persist with restore-on-failure), matching the ordered guard list in `contracts/gep-add-tool.md`, completely bypassing the existing creation-path logic (type registry dispatch, `with_resources`/`with_prompts`, the "directory already exists" duplicate guard, and `ModuleFactory.build()`).

**Rationale**: The existing creation path's duplicate guard (`if src_dir.exists(): ... already exists ...`) is the *opposite* of what `--add-tool` needs (entry point **must** already exist). Branching early — rather than threading an `add_tool` flag through every existing guard — keeps both code paths readable and avoids accidentally weakening the creation path's guards.

**Alternatives considered**: Inverting/parameterizing the single existing guard with an `invert: bool` flag. Rejected — the two flows diverge enough afterward (factory dispatch vs. append-to-file mutation, full-directory creation vs. single-file mutation) that a shared linear function would need several more conditionals than a clean early branch.

---

## R-003: `--name` and `--param` name validation

**Decision**: Reuse `core.name_utils.validate_module_name` (the existing strict snake_case `^[a-z][a-z0-9]*(_[a-z0-9]+)*$` check, already used by `generate-model`/`generate-use-case`/etc.) for both `--name` and the `name` portion of every `--param name:type` value, per the `/speckit-clarify` decision. `--param` values are split on the **first** `:` only (tool/parameter names cannot themselves contain `:`, so this is unambiguous and tolerant of type expressions that might otherwise confuse a naive split).

In addition, both `--name` and every `--param` name are rejected if `keyword.iskeyword(name)` is true (hard keywords such as `class`, `import`, `return`), per the revised 2026-10-16 clarification. Soft keywords (`keyword.issoftkeyword`, e.g. `match`, `type`) are valid identifiers and are not rejected. Without this check, a keyword name would produce `async def class(...)`, which `ast.parse` rejects — the T021 safety net would catch it, but with a misleading "regenerate the entry point" message.

**Rationale**: Clarification session resolved this explicitly — consistency with the rest of the CLI's naming conventions, plus the minimal extra rule needed to guarantee the generated code parses.

**Alternatives considered**: A looser "any valid Python identifier" rule. Rejected per clarification answer.

---

## R-004: Type-expression grammar validation (`--param` type, `--returns`)

**Decision**: Parse the candidate type string with `ast.parse(expr, mode="eval")` (the stdlib `ast` module, already used elsewhere in this codebase by `core/structure_validator.py`) and walk the resulting expression tree, accepting only a constrained grammar:

- **Top-level accepted node kinds**: `Name` (`str`, `int`, `MyModel`), `Attribute` (dotted names, e.g. `typing.Optional`), `Subscript` (generics, e.g. `list[str]`, `dict[str, int]`, `Optional[str]`), `BinOp` with a `BitOr` operator (PEP 604 unions, e.g. `str | None`), and the bare constant `None`.
- **Nested node kinds allowed only inside a `Subscript`'s index** (so generics and literals compose correctly): `Tuple`/`List` (multi-argument generics), further `Name`/`Attribute`/`Subscript`/`BinOp(BitOr)`, the `Constant` node for `None`, `Ellipsis` (`tuple[int, ...]`), and string/int/bool constants (so `typing.Literal["a", "b"]` and similar remain valid).
- **Rejected everywhere**: `Call` (function calls), `Lambda`, any comprehension, `BoolOp`, `Compare`, `UnaryOp`/`BinOp` other than `|`, `Starred`, and a **bare** top-level `Constant`/string/number/f-string standing in for the whole type (e.g. `--returns "hello"` or `--returns "print('x')"` is rejected because `print('x')` parses as a `Call` and a bare string parses as a top-level `Constant`, neither of which is an accepted top-level kind).

A syntax error from `ast.parse` itself (the string isn't even a parseable Python expression) is treated the same as a grammar rejection — both produce the same `ScaffoldError` message identifying the offending value.

**Rationale**: The clarification session resolved that validation must reject arbitrary Python expressions and accept only recognizable type-expression shapes. Reusing `ast` (rather than hand-rolled regex) correctly handles nested generics and avoids reinventing a parser, and mirrors the project's existing choice of `ast` for source inspection in `structure_validator.py`.

**Alternatives considered**: Regex-based validation (e.g., `^[\w.]+(\[.+\])?$`). Rejected — cannot correctly reject non-type expressions like `print('x')` while accepting legitimate nested generics like `dict[str, list[int]]`; `ast`-based structural validation is both simpler and stricter. A full `typing`-aware evaluator (actually importing/resolving the expression). Rejected — the spec's Assumptions explicitly scope validation to syntax/shape only, not import-resolution.

---

## R-005: Duplicate tool-name detection

**Decision**: Read the target `tools.py` source, parse it with `ast.parse`, and walk `AsyncFunctionDef`/`FunctionDef` nodes looking for a decorator that is a `Call` whose `func` is an `Attribute` named `tool` (i.e., matches `<anything>.tool(...)`, covering `@mcp.tool("name")`) with a string-literal first argument. The set of taken names is the union of (a) those string literals (registered tool names), (b) the names of every function defined directly inside `bind_tools`'s body (per the `/speckit-clarify` decision that a registered name and its function name can differ, and both collide), and (c) the reserved name `bind_tools` itself (spec Edge Cases). Reject `--add-tool --name X` if `X` is in that set.

**Rationale**: AST-based parsing is robust against incidental text matches (e.g., a tool name mentioned only in a comment or docstring) that a regex/substring search could misfire on, and is consistent with the project's existing `ast`-based source inspection (`structure_validator.py`) and with R-004's approach.

**Alternatives considered**: A plain substring/regex search for `@mcp.tool("name")`. Rejected — more fragile (false positives from comments/docstrings, false negatives from reformatted decorator calls) for only a small implementation cost saved.

---

## R-006: `tools.py` registrar-list pattern + new `ModuleBuilder.append_to_file` primitive (no anchor comments)

> **⚠️ Partially superseded (2026-10-15)**: the registrar-list restructuring below (`_TOOL_REGISTRARS`, `_register_tool`, `_bind_<name>`) was **reversed** — see `plan.md` Constraints. `tools.py.jinja2` is **not** restructured; new stubs are rendered as a 4-space-indented nested `@mcp.tool(...)` function and appended to the end of `tools.py`, landing inside `bind_tools` because `bind_tools` MUST be the last top-level statement in the file. Still valid from this section: the no-anchor rule and the `AppendToFile`/`append_to_file` primitive (item 2). The legacy guard checks `async def bind_tools` as the last top-level statement (not `_TOOL_REGISTRARS`), and filesystem write failures are handled per FR-019 (see "Write-failure handling" below), not left as tracebacks.

**Decision**: Do **not** use a literal "do not remove" anchor comment as the insertion mechanism for `tools.py`/`test_tools.py` (this is the exact pattern used by the reference project `ca-scaffold-py`'s `# ANCHOR_TOOLS_BIND`, which is explicitly rejected for this codebase — a scaffold should not generate code containing instructions telling a developer not to delete a comment). Instead:

1. Restructure `templates/entry_point/mcp/tools.py.jinja2` around a **registrar-list pattern**:

   ```python
   _TOOL_REGISTRARS: list[Callable[[FastMCP], None]] = []


   def _register_tool(fn):
       """Register *fn* to run during bind_tools(); used as a decorator."""
       _TOOL_REGISTRARS.append(fn)
       return fn


   @_register_tool
   def _bind_example_tool(mcp: FastMCP) -> None:
       @mcp.tool("example_tool")
       async def example_tool(query: str) -> str:
           """Example tool stub — replace with your implementation."""
           return f"result for: {query}"


   @inject
   async def bind_tools(mcp: FastMCP, ...) -> None:
       """Bind all MCP tools to the server instance."""
       for registrar in _TOOL_REGISTRARS:
           registrar(mcp)
   ```

   `bind_tools()` is written once by the base `gep --type mcp` creation path and is **never modified again** by `--add-tool`. `templates/entry_point/mcp/test_tools.py.jinja2` requires no structural change at all (no anchor, no marker) — new registration tests are simply appended to the end of the file.

2. Add a new, generic **`ModuleBuilder.append_to_file(path, content)`** primitive (backed by a new `AppendToFile` `FileOperation` model and `FileWriter._apply_append_to_file`), independent of and without modifying the existing `insert_after`/`InsertAfter`/`_apply_insert_after`. Its semantics: if `path` exists, append `content` to the end of the file (with appropriate blank-line separation); if `path` does **not** exist, create it (including parent directories) with `content` as its initial contents.

3. `--add-tool` renders a **complete top-level block** — `@_register_tool` decorator plus a `_bind_<name>(mcp)` function wrapping the actual `@mcp.tool("<name>")`-decorated stub — and calls `builder.append_to_file(tools_py_path, content=<rendered block>)`, and the equivalent registration-test block appended to `test_tools.py` via `builder.append_to_file(test_tools_py_path, content=<rendered test>)`.

**Rationale**: `AppendToFile` needs no textual marker at all — "append to the end of the file" is a well-defined, unambiguous operation on its own, so there is nothing a developer could be tempted to delete. The registrar-list pattern is ordinary, idiomatic Python (a module-level list plus a decorator) rather than a magic comment, and is trivially inspectable via `ast` for the legacy-project guard (R-007). This also keeps `bind_tools()` itself completely static after initial generation, which is easier to reason about than a function body that silently grows every time a tool is added.

**Alternatives considered**:
- Keeping the anchor-comment approach (`scaffold:add-tool-anchor` / `scaffold:add-tool-test-anchor`) reusing the existing `insert_after`. Rejected per explicit project decision — this is the same "magic comment" style the reference project uses and that this codebase wants to avoid in generated output.
- Extending `insert_after`/`InsertAfter` itself to support "insert at end of file" semantics without an anchor. Rejected — conflates two different operations (insert-after-a-textual-match vs. append-at-end-of-file-or-create) in one primitive; a separate, narrowly-scoped `AppendToFile` is clearer and keeps `insert_after`'s existing contract and tests completely untouched.
- Restructuring `tools.py` so every tool (including `example_tool`) is a bare top-level `@mcp.tool(...)`-decorated function with no `bind_tools()` wrapper at all. Rejected — `bind_tools()` is the existing, already-tested dependency-injection entry point (`@inject`) that every consumer (`app.py`) calls; removing it would be a larger, unrelated behavioral change to the base MCP entry point.

**Pre-flight guard (not relying on `append_to_file`'s own exceptions)**: Before queuing any `append_to_file` operation, `--add-tool` reads `tools.py` and `test_tools.py` directly and checks — via `ast` — that `tools.py`'s last top-level statement is `async def bind_tools` and that `test_tools.py` has the registration-test structure (top-level `_make_mock_mcp`, imports of `bind_tools` and `asyncio`) (R-007/FR-017). If either file is missing, unreadable, or fails its structural check, the command fails immediately with a friendly `[red]Error:[/red] ... [dim]Hint:[/dim] Regenerate the entry point with \`scaffold gep --type mcp\` ...` message and exits code 1 — **before** calling `builder.persist()`. Because `--add-tool`'s own pre-flight guard is the only thing deciding whether to queue the operation, `FileWriter._apply_append_to_file` itself never needs to raise a "marker not found" error the way `_apply_insert_after` does — it can only fail for genuine filesystem errors (e.g. permission denied, disk full).

**Write-failure handling (FR-019)**: `--add-tool` keeps the original text of both files from the pre-flight `Path.read_text()` calls, checks `os.access(path, os.W_OK)` on both before queuing any operation (failing with a hint if either is not writable), and wraps `builder.persist()` in `try/except OSError`; on failure it writes both original texts back and exits `1` with a hint. Either both files change or neither does. As a final safety net, before persisting it runs `ast.parse(original_tools_py + rendered_stub)`; a parse failure raises the FR-017 regeneration error instead of writing an unparseable file.

**Compatibility note**: Projects whose `tools.py` has any top-level statement after `bind_tools` (e.g. a hand-added helper function or `__all__`) are treated as incompatible by this guard, since appending an indented block there would land in the wrong scope. The error hint tells the developer to move `bind_tools` back to the end of the file or regenerate.

---

## R-007: Where the duplicate / `bind_tools` / test-structure pre-flight checks read `tools.py` and `test_tools.py`

**Decision**: These checks read the file directly via `Path.read_text()` inside the new `--add-tool` command path (`core/mcp_tool_spec.py` helper functions take the source string and return structured results), not through `ModuleBuilder`. `ModuleBuilder` is reserved for *queuing* operations (`add_file`/`append_to_file`/`insert_after`/`delete_file`) that are later persisted; reading existing file content to make guard decisions is orthogonal and already has precedent in this command module (e.g., the existing `if src_dir.exists(): ...` duplicate-directory guard in the creation path reads the filesystem directly, not through the builder).

**Rationale**: Keeps `ModuleBuilder`'s responsibility (collect-then-persist) unchanged and avoids adding a "read current file" API to it that nothing else needs.

---

## R-008: Dry-run preview content (not just paths)

**Decision**: `FileWriter._dry_run` today returns only the **path** that would be touched by an `InsertAfter` operation, not the content that would be inserted (`result.append(op.path)`, no content); the new `AppendToFile` operation follows the exact same dry-run contract (path only, no content, no disk write). Because the spec (US3 / FR-016 / SC-003) requires the `--dry-run` preview to show the **actual stub code** that would be appended, the `--add-tool` command path renders the tool-stub and test-stub snippets **before** calling `builder.persist()` (it already must, to construct the `append_to_file` calls), and prints them directly via `rich.syntax.Syntax` alongside the existing dry-run file-tree output — independent of `builder.persist()`'s return value.

**Rationale**: This avoids changing the shared `FileWriter` dry-run contract (which the unrelated `config.py` `HOST`/`PORT` insertion in `ep_mcp.py` also relies on via the untouched `InsertAfter`, today only ever shown as a bare path in existing `--dry-run` output), keeping the blast radius of this feature limited to the `--add-tool` path.

**Alternatives considered**: Extending `FileWriter._dry_run` to carry and return content generally for every operation kind. Rejected for this feature — broader than needed and would change dry-run output for the unrelated existing `config.py` insertion, which is out of this feature's scope.

---

## R-009: `--description` docstring safety

**Decision**: Reject (do not escape) any `--description` value containing a triple-quote sequence (`"""` or `'''`) or an unterminated/odd number of backslashes immediately preceding the string's own closing delimiter, with a specific `ScaffoldError` naming the problem. The rendered docstring template wraps the (validated) description in triple double quotes (`"""{{ description }}"""`), matching the existing `tools.py.jinja2` docstring style.

**Rationale**: Per the `/speckit-clarify` decision — fail fast and never silently rewrite user-supplied text, consistent with every other `--add-tool` input validation in this feature.

**Alternatives considered**: Auto-escaping. Rejected per clarification answer.

---

## R-010: New Jinja2 templates and required template-level tests

**Decision**: Add two new template files under `templates/entry_point/mcp/`:

> **Updated (2026-10-15)**: `tool_stub.py.jinja2` renders a 4-space-indented nested function (no `@_register_tool` / `_bind_<name>` wrapper), per `plan.md` and `tasks.md` T009.

- `tool_stub.py.jinja2` — renders the appended block, indented to sit inside `bind_tools` (matching the shape of the nested `example_tool` in the base template; one leading blank line, since it lands inside a function):
  ```jinja2

      @mcp.tool("{{ name }}")
      async def {{ name }}({% for p in params %}{{ p.name }}: {{ p.type }}{% if not loop.last %}, {% endif %}{% endfor %}) -> {{ returns }}:
          """{{ docstring }}"""
          raise NotImplementedError("Tool '{{ name }}' is not yet implemented.")
  ```
- `test_tool_stub.py.jinja2` — renders the appended registration assertion:
  ```jinja2


  def test_bind_tools_registers_{{ name }}() -> None:
      """Calling bind_tools registers '{{ name }}' on the mcp instance."""
      mock_mcp, registered = _make_mock_mcp()
      fn = getattr(bind_tools, "__wrapped__", bind_tools)
      asyncio.run(fn(mock_mcp))
      assert "{{ name }}" in registered
  ```

Both are rendered via `builder.render(template_name, context_dict)` (the existing `TemplateRenderer`), never via `render_string`/f-strings, per Constitution Principle II, and both are appended at the end of their target file via `builder.append_to_file(...)` (R-006) — no anchor/marker involved. Each new template gets at least one rendering unit test added to `tests/templates/test_entry_point_templates.py` (the file that already covers the `entry_point/mcp` template group), asserting the rendered snippet contains the expected function name, the 4-space-indented `@mcp.tool("<name>")` decorator (and no `@_register_tool`), signature, and `raise NotImplementedError` body — satisfying Principle II's "dedicated unit tests... assert structural correctness" requirement without needing a new `tests/templates/` subdirectory (the `entry_point/mcp` group is already covered there).

**Rationale**: Keeps generation strictly template-driven and testable, matching the pattern used for every other MCP primitive file.

---

## R-011: `tools.py` registrar-list rewrite is backward-safe for the base creation path

> **⚠️ Superseded (2026-10-15)**: the registrar-list rewrite was reversed — `tools.py.jinja2` is unchanged by this feature (see `plan.md` Constraints and `tasks.md` T005/T006), so the base `gep --type mcp` creation path is trivially unaffected. The text below is kept for history only.

**Decision (historical)**: Restructuring `tools.py.jinja2` around the `_TOOL_REGISTRARS` registrar-list pattern (R-006) changes *how* `example_tool` is wired — it becomes `_bind_example_tool`, a `@_register_tool`-decorated function that `bind_tools()` now invokes indirectly via the registrar loop instead of defining `example_tool` directly in its own body — but it does not change `example_tool`'s externally observable behavior: calling `bind_tools(mcp)` still registers a tool named `"example_tool"` with the same signature, docstring, and return value. `test_tools.py.jinja2`'s existing assertions (`test_bind_tools_registers_example_tool`, `test_example_tool_returns_expected_result`, `test_bind_tools_is_async_callable`) continue to pass unchanged, since they only observe `bind_tools()`'s behavior through the mocked `mcp.tool(...)` registration, never its internal implementation.

**Rationale**: Confirms the plan's constraint that the base creation behavior of `gep --type mcp` remains unaffected — a zero-regression change for every project generated going forward.
