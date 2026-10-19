# Feature Specification: Incremental MCP Tool Addition

**Feature Branch**: `021-mcp-add-tool`

**Created**: 2026-10-15

**Status**: Draft

**Input**: User description: "Extend `scaffold gep` with a `--add-tool` capability that inserts a single new tool stub into an already-generated MCP entry point's `tools.py` (and its test), without regenerating the whole entry point and without generating a full Clean Architecture chain (domain model, use case, gateway, adapter) per tool."

## Clarifications

### Session 2026-10-15

- Q: Should the `name` portion of each `--param name:type` value follow the same snake_case rule as `--name`, or just be a valid Python identifier? → A: Require snake_case (same rule as `--name`)
- Q: How permissive should validation of a `--param` type or `--returns` value be — any valid Python expression, or a recognizable type-expression shape only? → A: Restrict to recognizable type-expression shapes (identifiers, subscripted generics like `list[str]`, or unions with `|`); reject arbitrary expressions such as function calls
- Q: When `--description` contains characters that could break a Python docstring (e.g., an embedded triple-quote sequence), should the command reject it outright or auto-escape/sanitize it? → A: Reject outright with an actionable error identifying the offending value; never silently mutate user-supplied text
- Q: When `tools.py` is valid but its test file (`test_tools.py`) is missing or no longer has the expected structure, what should `--add-tool` do? → A: Fail with an actionable error and modify no file (treated as an incompatible project)
- Q: Should `--name` and `--param` names that are Python reserved keywords (e.g., `class`, `import`) be rejected beyond snake_case validation? → A: Yes — reject hard Python keywords (e.g., `class`, `import`, `return`) with an error naming the keyword; soft keywords that are valid identifiers (e.g., `match`, `type`) remain allowed (revised 2026-10-16, replacing the earlier "no extra check" answer, so that `--add-tool` never writes code that cannot be parsed)
- Q: When a `--param` or `--returns` type needs an import (e.g., `Path`, a domain model), should `--add-tool` add import statements? → A: Never add imports; type text is inserted verbatim and the developer adds any imports
- Q: For the duplicate-tool check, what counts as "already exists" when a registered tool name differs from its function name? → A: Conflict if `--name` matches any registered `@mcp.tool("…")` name OR any function name defined inside `bind_tools`
- Q: If `tools.py` is written but writing `test_tools.py` then fails, what happens to `tools.py`? → A: Validate both files are readable/writable before writing; if a write still fails, restore `tools.py`'s original contents — both files change or neither does

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Add a new tool to an existing MCP server (Priority: P1)

As a developer who has already scaffolded an MCP entry point with `scaffold gep --type mcp`, I want to add a new tool to it by running a single command, so that I don't have to hand-edit `tools.py` to wire up the function signature, decorator, and docstring correctly every time I need a new capability.

**Why this priority**: This is the core value of the feature. Without it, developers have no supported way to grow an MCP server's tool surface after initial generation — they must either regenerate from scratch (losing existing tools) or edit generated files manually (error-prone, inconsistent with scaffold conventions).

**Independent Test**: Can be fully tested by running `scaffold gep --type mcp` to create a baseline entry point, then running `scaffold gep --type mcp --add-tool --name create_file --param path:str --param content:str --returns str --description "Creates a file on disk"` and verifying a new `create_file` tool stub appears in `tools.py`, registered under that name, with the given parameters, return type, and docstring — while all previously existing tools remain untouched.

**Acceptance Scenarios**:

1. **Given** an MCP entry point already exists, **When** the developer runs `scaffold gep --type mcp --add-tool --name create_file --param path:str --param content:str --returns str --description "Creates a file on disk"`, **Then** a new async tool function named `create_file` is added to `tools.py`, registered so the MCP server exposes it under the name `create_file`, with a `path: str` and `content: str` signature, a `str` return type, the given docstring, and a body that clearly signals the behavior is not yet implemented.
2. **Given** the same command is run with no `--param` flags at all, **When** the command completes, **Then** the generated tool stub takes no parameters beyond what the tool-binding mechanism itself requires.
3. **Given** `--returns` and `--description` are omitted, **When** the command completes, **Then** the generated tool stub defaults its return type to `str` and uses a generic, clearly-marked placeholder docstring.
4. **Given** the command succeeds, **Then** all tools that existed in `tools.py` before the command ran are still present and unchanged.
5. **Given** the command succeeds, **Then** the corresponding test file for `tools.py` is updated (or newly includes an assertion) confirming the new tool name is registered, without asserting anything about the stub's internal (not-yet-implemented) behavior.

---

### User Story 2 - Clear guardrails prevent invalid or conflicting requests (Priority: P2)

As a developer, when I misuse `--add-tool` — by targeting a project that has no MCP entry point yet, naming a tool that already exists, combining it with incompatible flags, or supplying a malformed name/parameter/type — I want an immediate, actionable error message instead of a confusing failure or a corrupted file, so I can correct my command and move on.

**Why this priority**: Guardrails protect the integrity of generated projects and the developer's trust in the tool. Without them, a mistyped command could silently create duplicate tools, write to the wrong project, or leave `tools.py` in a broken state.

**Independent Test**: Can be fully tested by running `--add-tool` against a project without an MCP entry point and verifying a clear, actionable failure; then against a project that already has a tool with the same `--name` and verifying a duplicate-tool failure; then combining `--add-tool` with each incompatible flag and verifying each is rejected.

**Acceptance Scenarios**:

1. **Given** a project with no MCP entry point generated yet, **When** `scaffold gep --type mcp --add-tool --name create_file` is run, **Then** the command fails with a message explaining the entry point does not exist yet and recommending `scaffold gep --type mcp` be run first.
2. **Given** an MCP entry point whose `tools.py` already registers a tool named `create_file` (via `@mcp.tool("create_file")`) or defines a function named `create_file` inside `bind_tools`, **When** `scaffold gep --type mcp --add-tool --name create_file` is run again with that same name, **Then** the command fails with a message stating a tool with that name already exists.
3. **Given** `--add-tool` is combined with `--swagger`, `--enable-kafka`, `--enable-mcp-client`, `--with-resources`, or `--with-prompts`, **When** the command is run, **Then** it fails with a message stating that `--add-tool` is incompatible with that flag.
4. **Given** `--add-tool` is combined with any `--type` other than `mcp` (or `--type` is omitted), **When** the command is run, **Then** it fails with a message stating `--add-tool` is only valid together with `--type mcp`.
5. **Given** `--add-tool` is passed without `--name`, **When** the command is run, **Then** it fails stating `--name` is required.
6. **Given** `--name` does not follow the project's snake_case naming rules, **When** the command is run, **Then** it fails with the same style of naming error used by other module-generating commands in the CLI. **Given** `--name` (or a `--param` name) is a Python reserved keyword such as `class`, **Then** it fails with an error naming the keyword.
7. **Given** a `--param` value does not match the `name:type` format, its `name` portion is not valid snake_case, or its `type` portion is not a recognizable type-expression, **When** the command is run, **Then** it fails identifying the specific offending `--param` value.
8. **Given** `--returns` is supplied but is not a recognizable type-expression (e.g., it is a function call or a bare literal rather than a name, dotted name, subscripted generic, or union), **When** the command is run, **Then** it fails identifying the invalid value.
9. **Given** an MCP entry point was generated by a scaffold version that does not support incremental tool insertion (no supported insertion point in its files), **When** `--add-tool` is run against it, **Then** the command fails with a clear message recommending the entry point be regenerated, rather than crashing or partially modifying the file.
10. **Given** an MCP entry point whose `tools.py` is valid but whose `test_tools.py` is missing or lacks the expected registration-test structure, **When** `--add-tool` is run, **Then** the command fails with an actionable message and modifies no file.

---

### User Story 3 - Preview the change before writing it (Priority: P3)

As a developer, I want to preview exactly what `--add-tool` would insert and where, without modifying any files, so I can review the generated stub and test change before committing to it.

**Why this priority**: Preview-before-write is an existing convention across `scaffold gep`; extending it to `--add-tool` keeps the experience consistent and gives developers confidence before altering a file they already maintain by hand.

**Independent Test**: Can be fully tested by running the same `--add-tool` command twice — once with `--dry-run` and once without — and confirming the dry run's preview (files touched, tool stub content, test update) matches what the real run actually produces, while the dry run itself leaves disk contents unchanged.

**Acceptance Scenarios**:

1. **Given** a valid `--add-tool` invocation with `--dry-run`, **When** the command runs, **Then** it prints a preview showing which file(s) would be modified and the tool stub (and test addition) that would be inserted, without writing to disk.
2. **Given** the same invocation is immediately re-run without `--dry-run`, **When** the command completes, **Then** the actual changes made to disk match what the dry run previewed.

---

### Edge Cases

- What happens when `--param` is repeated with the same parameter name twice (e.g., `--param path:str --param path:int`)? The command should reject it as a duplicate parameter name within the same tool.
- What happens when `--name` collides with a name already reserved by the tool-binding mechanism itself (e.g., the binding function's own name)? The command should reject it as invalid, since it cannot be distinguished from a real duplicate-tool conflict in practice.
- How does the system handle an entry point directory that exists but whose `tools.py` or `test_tools.py` file is missing, unreadable, or (for the test file) lacks the expected registration-test structure? The command should fail with a clear message rather than crashing, modifying no file and treating the project as incompatible with `--add-tool` until repaired or regenerated.
- What happens when `--name` or a `--param` name is a Python reserved keyword (e.g., `class`)? It is rejected before any file is touched, with an error naming the keyword, because the generated code would not be valid Python. Soft keywords that are valid identifiers (e.g., `match`, `type`) are allowed.
- What happens if writing the second file fails after `tools.py` was already modified (e.g., permission error, full disk)? `tools.py` is restored to its original contents and the command exits with an error; no partially-applied change remains.
- How does the system handle a `--description` value that would break the generated docstring (e.g., containing the docstring's own triple-quote sequence)? The command rejects it outright with an actionable error naming the problem, rather than silently rewriting the user's text.
- What happens if `--add-tool` is combined with `--dry-run` targeting a project with no MCP entry point? The missing-entry-point failure takes precedence over the preview — no partial preview is shown.
- What happens when `--param` or `--returns` is given a syntactically valid Python expression that is not a type-expression (e.g., a function call like `print('x')` or a bare string literal)? It is rejected with the same error used for malformed type values, since it is not a recognizable type-expression shape.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The `gep` / `generate-entry-point` command MUST support a new `--add-tool` flag, usable only together with `--type mcp`.
- **FR-002**: `--add-tool` MUST require `--name`; the command MUST fail with an actionable error, before modifying any file, if `--name` is missing.
- **FR-003**: `--name` MUST be validated using the same snake_case naming rules already applied to module/class-generating commands elsewhere in the CLI; invalid names MUST be rejected with an error in that same style. Additionally, `--name` MUST NOT be a hard Python reserved keyword (e.g., `class`, `import`); such names MUST be rejected with an error naming the keyword.
- **FR-004**: `--param` MUST be a repeatable flag accepting zero or more values, each in the form `name:type`; the order supplied on the command line MUST be preserved in the generated tool's parameter list.
- **FR-005**: Each `--param` value MUST be rejected, with the specific offending value identified in the error, if it does not match the `name:type` format, if its `name` portion does not follow the same snake_case naming and reserved-keyword rules required for `--name` (FR-003), or if its `type` portion is not a recognizable Python type-expression (a bare name, dotted name, or a subscripted/union type such as `list[str]` or `str | None`) — arbitrary expressions such as function calls or literals MUST be rejected.
- **FR-006**: `--param` values MUST be rejected if two or more share the same parameter name within the same `--add-tool` invocation.
- **FR-007**: `--returns` MUST be optional and default to `str` when omitted; when supplied, it MUST be a recognizable Python type-expression as defined in FR-005, or the command MUST fail identifying the invalid value.
- **FR-008**: `--description` MUST be optional; when supplied, its value MUST be used as the generated tool's docstring and MUST be rejected with an actionable error if it contains a sequence that would break Python docstring syntax (e.g., an embedded triple-quote); when omitted, a generic, clearly-marked placeholder docstring MUST be used instead.
- **FR-009**: The command MUST fail with an actionable error — including a hint to run `scaffold gep --type mcp` first — when the target project does not yet have an MCP entry point generated.
- **FR-010**: The command MUST fail with a clear, specific error when the requested `--name` matches either an already-registered tool name (`@mcp.tool("…")`) or a function name already defined inside `bind_tools` in the project's `tools.py`, without modifying the file.
- **FR-011**: The command MUST reject `--add-tool` when combined with any of `--swagger`, `--enable-kafka`, `--enable-mcp-client`, `--with-resources`, or `--with-prompts`, with a message identifying the incompatible flag.
- **FR-012**: The command MUST reject `--add-tool` when combined with any `--type` value other than `mcp` (including when `--type` is omitted), with a message stating the required combination.
- **FR-013**: When all validations pass, the command MUST insert into `tools.py` exactly one new async tool function, registered to be exposed under the requested `--name`, with a signature built from the supplied `--param` values and `--returns` type, the resolved docstring, and a body that signals the behavior is not yet implemented rather than containing real logic. Type text from `--param` and `--returns` MUST be inserted verbatim; no import statements are added or changed.
- **FR-014**: The command MUST NOT generate, as part of `--add-tool`, any domain model, use case, gateway, or driven adapter; its generation scope is limited to the single tool stub described in FR-013.
- **FR-015**: The command MUST add to (or update) the test file corresponding to `tools.py` an assertion that the new tool is registered under the requested `--name`, without asserting on the stub's internal behavior.
- **FR-016**: `--add-tool` MUST support `--dry-run`, previewing the file(s) that would be touched and the content that would be inserted, without writing any changes to disk; the preview MUST match what an equivalent non-dry-run invocation actually produces.
- **FR-017**: The command MUST fail with a clear, actionable message — recommending the MCP entry point be regenerated — when the target project's `tools.py` was produced by a scaffold version that does not include the `bind_tools` async function pattern `--add-tool` relies on — or when `bind_tools` is not the last top-level statement in `tools.py` — instead of crashing or leaving the file partially modified. The same failure, raised before any write, MUST apply when `test_tools.py` is missing or lacks the expected registration-test structure.
- **FR-018**: `--add-tool` is explicitly out of scope for adding resources or prompts incrementally; `--resource` and `--prompt` equivalents are not part of this feature.
- **FR-019**: Before writing, the command MUST verify that both `tools.py` and `test_tools.py` are readable and writable; if a write fails after one file was already modified, the command MUST restore that file's original contents and exit with an error, so that either both files change or neither does.

### Key Entities

- **Tool Stub**: A single generated async function exposed as an MCP tool under a developer-chosen name, with a typed parameter list, return type, docstring, and a not-yet-implemented body — the sole artifact `--add-tool` produces per invocation.
- **MCP Tools Module**: The existing generated file (`tools.py`) that binds all of a project's MCP tools; `--add-tool` appends to it without disturbing previously defined tools.
- **Insertion Point**: A recognizable location within the MCP Tools Module defined by the presence of an `async def bind_tools` function as the last function in the file; `--add-tool` appends new tool stubs to the end of the file (inside `bind_tools`), so its absence marks a project as incompatible with `--add-tool`.
- **Tool Registration Test**: The test-file assertion confirming a given tool name is registered by the binding function, independent of whether the tool's own logic has been implemented yet.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can add a new MCP tool stub to an existing entry point with a single command, without manually editing any generated file.
- **SC-002**: 100% of invalid `--add-tool` invocations (missing/invalid `--name`, reserved-keyword names, malformed `--param`, invalid `--returns`, docstring-breaking `--description`, duplicate tool name, incompatible flag combinations, missing entry point, missing/unrecognizable test file, unsupported/legacy project) are rejected with an actionable, specific error message rather than a raw crash or stack trace.
- **SC-003**: The `--dry-run` preview for `--add-tool` matches, file-for-file and content-for-content, what an equivalent live run actually produces.
- **SC-004**: After a successful `--add-tool` run, the full set of previously existing tools and tests remains intact and passing, with the newly generated tool-registration test also passing.
- **SC-005**: Running `--add-tool` against a project generated by an unsupported (pre-feature) scaffold version fails predictably with a remediation hint, with zero instances of file corruption, partially-applied changes, or unhandled crashes observed.

## Assumptions

- `--add-tool` targets only `tools.py` and its corresponding test file; `resources.py`, `prompts.py`, and their tests are not touched by this feature, consistent with the explicit exclusion of incremental resource/prompt addition.
- Validating a supplied type annotation means confirming it is a recognizable Python type-expression — a bare name, dotted name, or a subscripted/union type such as `list[str]` or `str | None` — not that a referenced custom type actually exists or is importable; arbitrary expressions (function calls, literals, comprehensions) are rejected outright rather than passed through.
- Projects generated with `scaffold gep --type mcp` going forward (once this feature ships) will include `bind_tools` as the last function in the generated `tools.py`; projects generated before that point may lack this structure and must be regenerated to gain `--add-tool` support, per FR-017.
- The reused snake_case naming validation is the same mechanism already applied to other module/class-generating commands in this CLI, so no new naming rules are introduced by this feature; it applies uniformly to both `--name` and each `--param` name. The only additional name check is the hard-keyword rejection in FR-003, which also applies to both.
- The developer is responsible for adding imports for any non-builtin types referenced in `--param` or `--returns`; because generated `tools.py` uses `from __future__ import annotations`, unresolved annotation names do not fail at import time.
- `--add-tool` is additive only: it does not provide a way to modify, rename, or remove a previously added tool; those remain manual edits, same as today.
