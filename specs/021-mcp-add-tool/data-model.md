# Data Model: Incremental MCP Tool Addition

**Date**: 2026-10-15
**Feature**: `021-mcp-add-tool`

This feature has no persistent storage or domain data model in the traditional sense — it is a code-generation CLI command. The entities below are the in-memory request/validation objects and the file-level artifacts the spec's Key Entities map to concretely.

---

## `ToolSpec` (new, in-memory only)

Parsed, fully-validated representation of a single `--add-tool` invocation. Constructed after all CLI-level validation passes; consumed by template rendering.

**File**: `src/scaffold_ca_python/core/mcp_tool_spec.py` (new)

| Field | Type | Source | Validation |
|---|---|---|---|
| `name` | `str` | `--name` | Required; snake_case via `validate_module_name` (FR-002, FR-003) |
| `params` | `list[ParamSpec]` | `--param` (repeatable) | Zero or more; order preserved; no duplicate `name`s (FR-004, FR-006) |
| `returns` | `str` | `--returns` | Defaults to `"str"`; recognizable type-expression (FR-007) |
| `docstring` | `str` | `--description` | Defaults to a generic placeholder; rejected if it would break docstring syntax (FR-008) |

**Represented as**: a small `@dataclass` or Pydantic `BaseModel` (consistent with the codebase's existing preference for Pydantic v2 models for structured CLI/context data, e.g. `ModuleContext`/`ProjectContext`). Pydantic is chosen for consistency with `models/context.py`'s pattern of field validators raising on bad input.

---

## `ParamSpec` (new, in-memory only)

A single parsed `--param name:type` value.

| Field | Type | Validation |
|---|---|---|
| `name` | `str` | snake_case via `validate_module_name` (per `/speckit-clarify` decision); unique within a `ToolSpec` |
| `type` | `str` | Recognizable Python type-expression per the grammar in `research.md` R-004 |

**Identity & uniqueness**: `name` MUST be unique within the `params` list of a single `--add-tool` invocation (FR-006). No uniqueness constraint crosses invocations — different tools may reuse the same parameter names.

---

## Key Entities from spec.md → concrete representation

### Tool Stub

The spec's abstract "Tool Stub" entity is realized as the rendered output of `templates/entry_point/mcp/tool_stub.py.jinja2`, fed with `{"name": ToolSpec.name, "params": [...], "returns": ToolSpec.returns, "docstring": ToolSpec.docstring}` — a complete top-level `@_register_tool`-decorated binding function. It is appended to `tools.py` via `ModuleBuilder.append_to_file`, never persisted as a model/object of its own beyond the rendered string.

### MCP Tools Module

The existing generated file `src/<pkg>/infrastructure/entry_points/mcp_server/tools.py`. No new file-level type is introduced; `--add-tool` reads it via `Path.read_text()` for guard checks (R-007) and mutates it via `ModuleBuilder.append_to_file`.

### Insertion Point

Realized as a structural symbol, not a textual marker (R-006): the module-level `_TOOL_REGISTRARS: list[Callable[[FastMCP], None]] = []` list defined in `tools.py` by `tools.py.jinja2`. New tools are appended as independent top-level blocks — nothing needs to be located or matched inside `tools.py` to append to it, since `append_to_file` always targets the end of the file. The structural symbol's only role is the legacy-project presence check below; `test_tools.py` has no equivalent symbol to check, since new registration tests are appended unconditionally.

**Presence check** (a project is "legacy"/incompatible per FR-017 when the symbol is absent), implemented via `ast` rather than a substring search so that reformatted or re-indented source still matches correctly:

```python
def has_registrar_pattern(tools_py_source: str) -> bool:
    """Return whether tools_py_source defines a module-level `_TOOL_REGISTRARS` symbol."""
    module = ast.parse(tools_py_source)
    return any(
        isinstance(node, (ast.Assign, ast.AnnAssign))
        and any(
            isinstance(target, ast.Name) and target.id == "_TOOL_REGISTRARS"
            for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        )
        for node in module.body
    )
```

### Tool Registration Test

Realized as the rendered output of `templates/entry_point/mcp/test_tool_stub.py.jinja2`, appended to `test_tools.py` via the same `append_to_file` mechanism, parallel to the existing `test_bind_tools_registers_example_tool` test already in the base template.

---

## Existing entities read, not modified

| Entity | File | Role in this feature |
|---|---|---|
| `ProjectContext` / `ModuleContext` | `models/context.py` | Reused unchanged to resolve `python_package` and locate `tools.py`/`test_tools.py` paths, exactly as the existing `gep --type mcp` creation path does |
| `GeneratedFile` / `CreateFile` / `DeleteFile` / `InsertAfter` | `models/file_operation.py` | None of these are queued by this feature; `InsertAfter` in particular remains untouched and is still used elsewhere (e.g. `ep_mcp.py`'s `HOST`/`PORT` injection into `config.py`) |
| `ModuleBuilder` | `core/module_builder.py` | Used for `builder.render(...)` and the new `builder.append_to_file(...)` (see "New entities introduced" below); `insert_after` remains available/unchanged for other callers but is not used by this feature |

## New entities introduced by this feature

| Entity | File | Role |
|---|---|---|
| `AppendToFile` | `models/file_operation.py` | New `FileOperation` kind: append `content` to the end of `path`, creating `path` (and parent directories) first if it does not yet exist. Added alongside the existing `CreateFile`/`DeleteFile`/`InsertAfter` kinds; does not replace or modify any of them |
| `ModuleBuilder.append_to_file(path, content)` | `core/module_builder.py` | Queues an `AppendToFile` operation, mirroring the existing `insert_after(path, anchor, content)` method's signature style |
| `FileWriter._apply_append_to_file(op)` | `core/file_writer.py` | Executes a queued `AppendToFile` operation during `persist()`, alongside the existing `_apply_insert_after`. When `path` already exists, its trailing blank lines are normalized to a single newline before `content` is appended — `content` itself (as rendered by `tool_stub.py.jinja2`/`test_tool_stub.py.jinja2`, each starting with two leading blank lines) supplies the resulting two-blank-line separation expected before a new top-level definition, per `tasks.md` T013. When `path` does not exist, any leading blank lines in `content` are stripped before it becomes the file's initial contents |

---

## Validation Rules Summary (cross-reference to FRs)

| Rule | Enforced by | FR |
|---|---|---|
| `--name` required when `--add-tool` set | CLI guard in `generate_entry_point.py` | FR-002 |
| `--name` / each `--param` name is snake_case | `validate_module_name` (reused) | FR-003, FR-005 (name portion) |
| `--param` matches `name:type`, split on first `:` | `mcp_tool_spec.parse_param` | FR-004, FR-005 |
| `--param` type / `--returns` is a recognizable type-expression | `mcp_tool_spec.validate_type_expression` (ast-based, R-004) | FR-005, FR-007 |
| No duplicate `--param` names within one invocation | `mcp_tool_spec.build_tool_spec` (or `ToolSpec` validator) | FR-006 |
| `--description` safe for docstring embedding | `mcp_tool_spec.validate_description` | FR-008 |
| MCP entry point must already exist | CLI guard (inverse of creation-path duplicate guard) | FR-009 |
| Tool name not already registered in `tools.py` | `mcp_tool_spec.find_existing_tool_names` (ast-based, R-005) | FR-010 |
| `--add-tool` incompatible with creation-only flags | CLI guard | FR-011 |
| `--add-tool` only valid with `--type mcp` | CLI guard | FR-012 |
| `_TOOL_REGISTRARS` registrar-list symbol present in `tools.py` | `mcp_tool_spec.has_registrar_pattern` (ast-based) | FR-017 |
