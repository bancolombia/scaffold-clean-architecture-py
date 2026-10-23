# Research: SOLID refactor and comment cleanup

Phase 0 of [plan.md](plan.md). The Technical Context had no `NEEDS CLARIFICATION` markers. This document records the design decisions the spec leaves open.

## R-01: Where each entry-point type's knowledge lives

- **Decision**: An abstract base class `EntryPointFactory` in `factory/entry_points/base.py` implements the `ModuleFactory` Protocol. It declares these `ClassVar`s:
  - `subdir: str`
  - `supported_flags: frozenset[EntryPointFlag]`
  - `conflicts: tuple[EntryPointConflict, ...]`

  It also has `result_notes(project_root, pkg, type_key, *, dry_run) -> list[str]`. By default it returns the "main.py will be replaced…" / "main.py replaced…" notice. `EntryPointRestApi` overrides it with the `main.py` deletion and `[project.scripts]` update notes.
- **Rationale**: It removes the 4 conditional chains on `type_` in `_generate_entry_point_impl`: flags, conflicts, subdirectory and messages. `ClassVar`s make the declaration visible and checkable by mypy, and tests can inspect it without instantiating anything.
- **Alternatives considered**:
  - **A separate descriptor dataclass in the registry** (`{"restapi": EntryPointType(factory=…, subdir=…)}`): this splits the knowledge away from its factory and forces edits in two places.
  - **Methods on the Protocol**: this would break minimal fake factories, and a Protocol cannot provide defaults.

## R-02: Flag-compatibility messages without changing their text

- **Decision**: `EntryPointFlag` is an ordered table: `SWAGGER`, `ENABLE_MCP_CLIENT`, `MCP_PRIMITIVES`, `ENABLE_KAFKA`. `MCP_PRIMITIVES` groups `--with-resources` and `--with-prompts`. Each member has a label (`"--swagger"`, `"--enable-mcp-client"`, `"--with-resources and --with-prompts"`, `"--enable-kafka"`) and a verb (`is`/`are`).

  The command checks the flags in that order. When the current type does not include the flag in `supported_flags`, the message is derived from the registered types that do support it:
  - **Exactly one type supports it**: `"{label} {is|are} only valid with --type {that_type}."`
  - **More than one**: `"{label} {is|are} not valid with --type {current_type}."`
- **Rationale**: It reproduces the 3 current messages exactly:
  - `swagger` → restapi only;
  - `enable-mcp-client` → all except mcp;
  - primitives → mcp only.

  Every current type supports `--enable-kafka`, so it never fails, as today. A new type inherits consistent messages without touching the command.
- **Alternatives considered**:
  - **Each factory validates and returns its own message**: this duplicates texts across factories and makes the validation order fragile.
  - **Unify the messages into a new format**: this violates FR-003.

## R-03: Conflict guards between entry points

- **Decision**: `EntryPointConflict(label: str, subdir: str)`. For example, `restapi` declares `(("mcp_server", "mcp_server"), ("agent", "agent"))`. The check is generic in the command and keeps the current message and hint (`"Remove '{dir}' before adding {type_key}."`).
- **Rationale**: It keeps the current text, where restapi shows the directory name and mcp/agent show the `restapi` label.
- **Alternatives considered**: Derive conflicts automatically ("every other type is exclusive"). That changes behavior for `generic`, which has no conflicts today.

## R-04: Script registration in `[project.scripts]`

- **Decision**: `ModuleBuilder.set_project_script(entry_fn: str = "start_server")` stores a private `str | None`, and `persist()` applies it. `ep_restapi` calls `set_project_script()` and `ep_mcp` calls `set_project_script("main")`. For dry-run output, the read-only property `pending_project_script` is exposed.
- **Rationale**: It satisfies FR-009, because the magic keys `scripts_entry` and `scripts_entry_fn` disappear. It also follows the read-only property pattern `ModuleBuilder` already has (`pending_dependencies`).
- **Alternatives considered**: A new `FileOperation` for scripts. It would mix file operations with TOML mutations that `pyproject_writer` already handles.

## R-05: Factory parameters (`add_param`/`get_param`)

- **Decision**: `add_param`/`get_param` stay for build flags (`routes`, `enable_kafka`, `with_resources`…). The CLI options are grouped in `EntryPointOptions`, a frozen dataclass that the command transfers to the builder with a single method, `options.apply_to(builder, routes)`.
- **Rationale**: The spec only requires removing the implicit script channel. Changing the `ModuleFactory.build(builder)` Protocol to receive typed options would affect all 11 factories and `test_dry_run_parity.py`, which uses `add_param`. That scope increase has little value for this refactor.
- **Alternatives considered**: A generic `build(builder, options)` with a TypeVar. Recorded as a possible follow-up (it fits naturally with 024-typed-template-contexts).

## R-06: Where the registries live

- **Decision**:
  - `ENTRY_POINT_FACTORIES` in `factory/entry_points/__init__.py`.
  - `DRIVEN_ADAPTER_FACTORIES` in `factory/driven_adapters/__init__.py`.
  - `PIPELINE_PROVIDERS` in `factory/pipelines/__init__.py`.

  The single-entry `_REGISTRY` dicts (`model`, `use_case`, `helper`, `delete`) are removed, and those commands instantiate their factory directly.
- **Rationale**: SC-005 requires 0 modified files in `commands/` when adding a type. Single-entry registries provide no polymorphism.
- **Alternatives considered**: `importlib.metadata` entry points (plugins). This is over-engineering for a closed set of types.

## R-07: Shared command utilities

- **Decision**: `commands/_shared.py` provides:
  - **`console`**: a single Rich instance.
  - **`fail(message: str, hint: str | None = None) -> NoReturn`**.
  - **`require_project_root(not_found_message: str | None = PROJECT_NOT_FOUND) -> Path`**: by default it prints the standard text `"No scaffold-ca-python project found. Run 'scaffold ca' first."`. With `None`, it prints the `ScaffoldError` text, which keeps the detailed message of `--add-tool`.
  - **`validate_name_or_exit(name, validator)`**.
  - **`ensure_absent(path, project_root, *, kind: Literal["File", "Directory"], hint: str)`**.
  - **`print_dry_run_tree(title, paths, base)`**.
  - **`print_pending_dependencies(builder)`**.
  - **`build_and_persist(factory, builder) -> list[Path]`**.
  - **`dry_run_option(help: str = "Preview without writing.")`**: builds the `--dry-run` `typer.Option`. The `help` text is configurable because `ca` and `vs` use different texts.
- **Rationale**:
  - It removes the 9 copies of the project-root block, the 5 copies of the dry-run tree and the 10 copies of the `--dry-run` option.
  - `fail()` is not called lexically inside an `except`, so B904 does not apply and no `from None` is needed. The `from None` clauses that have no cause are removed.
  - The utilities live in `commands/` because they depend on Rich and Typer.
- **Alternatives considered**: A `Command` base class with a template method. Typer registers functions, not classes, so inheritance would add indirection with no benefit.

## R-08: Tests that depend on internal symbols

- **Decision**: These tests get adapted imports and registration points. Their behavioral assertions don't change:
  - **`tests/factory/test_registry.py`**: points to the new registries. `test_simple_command_registries_expose_single_key` is removed because it checks an internal detail the spec requires removing (FR-013). The fact that the simple commands still generate the same output is already covered elsewhere.
  - **`tests/factory/test_extensibility.py`**: the fake factory inherits from `EntryPointFactory` and is registered with `monkeypatch.setitem(ENTRY_POINT_FACTORIES, ...)`. An assertion that `commands/` was not touched is added.
  - **`tests/factory/test_dry_run_parity.py`**: imports the new registries.
  - **`test_ep_mcp.py` and `test_ep_restapi.py`**: check `pending_project_script` instead of `get_param("scripts_entry")`.
- **Rationale**: The spec's Assumptions allow reorganizing tests that import internal symbols, as long as their assertions on observable behavior don't change.

## R-09: Identifying the failed file in the `--add-tool` rollback

- **Decision**: Use `OSError.filename` (compared with the two paths) instead of searching for `"test_tools"` in the error text. When `filename` is `None`, keep the current default (`tools.py`). Restoring the originals moves to a `_restore(originals: dict[Path, str])` function.
- **Rationale**: It is robust, independent of language and platform, and removes the SIM108.

## R-10: Docstring style and comment policy

- **Decision**: Google style (`Args:`, `Returns:`, `Raises:`), using those sections only when they add something the signature doesn't say. One-line docstrings are the norm for private functions.

  These are removed:
  - the IDs `T0xx`, `FR-0xx`, `US-x`, `R-xx` and `Phase N`;
  - `# ----` banners;
  - lists of files and versions in factory docstrings;
  - comments that repeat the next line.

  Comments that explain *why* are kept, for example the `~=1.30.0` cap on `mcp` or the atomicity of `os.replace`.
- **Rationale**: This is the user's decision in the spec. Today NumPy style (`module_builder`, `file_writer`, `project_detector`) and Google style (`mcp_tool_spec`, `structure_validator`) coexist.
- **Alternatives considered**: Enable `D` (pydocstyle). The user ruled it out during initial planning; it remains a future option.

## R-11: Ruff configuration

- **Decision**:
  ```toml
  [tool.ruff.lint]
  select = ["E", "F", "I", "UP", "ANN", "B", "SIM", "C90"]

  [tool.ruff.lint.mccabe]
  max-complexity = 10
  ```
  B008 does not fire because Typer is used with `Annotated`, so no ignore is needed.

  During the migration, a temporary C901 `per-file-ignores` is added for the affected modules and removed in the last step (verifiable with `grep`).
- **Rationale**: The guardrail can be enabled first without leaving the branch red.

## R-12: `generate_project` and `generate_pipeline` with `ModuleBuilder`

- **Decision**:
  - **`generate_project`**:
    - builds a `ModuleBuilder(project_root=target_dir, …)`;
    - `file_writer`/`template_renderer` are optional parameters that the implementation receives;
    - the 7 root files and the 6 DI config files come from a `(relative_path, template)` table.
  - **`template_name`**: the `GeneratedFile`s of `ca` change from `""` to the real template name. This is not observable: neither the checksum nor the output uses it.
  - **`generate_pipeline`**:
    - uses `PipelineFactory` (one descriptor per provider: output path, template, display name) and `ModuleBuilder`;
    - takes optional, injectable `renderer`/`writer`.
- **Rationale**: It removes the module-level singletons (FR-014) and both `_tmpl()` helpers (FR-013). `TemplateRenderer.render()` and `render_string(_tmpl())` use the same `Environment`, so the output is identical; `test_dry_run_checksum.py` confirms it.

## R-13: Templates for the `ca` files that don't come from a template today

- **Decision**: Two new templates are created:
  - `project/package_init.py.jinja2` (`"""{{ name }} package."""`), for the package `__init__.py`;
  - `project/empty.jinja2`, for `src/tests/__init__.py`.

  The output is byte-for-byte identical.
- **Rationale**: It complies with Constitution II (every emitted file comes from a template). FR-004 was clarified to allow adding templates without modifying existing ones.
- **Alternatives considered**: Keep it as debt. Rejected because the cost is minimal and it removes the deviation.

## R-14: `[project.scripts]` is lost in the Rich output (C-3)

- **Decision**: Apply `rich.markup.escape()` to `[project.scripts]` in `EntryPointRestApi.result_notes`, in both dry-run and real mode.
- **Rationale**:
  - Running the CLI showed that today it prints `Would update : my_app = …`, because Rich interprets the section as markup. `[project.dependencies]` was already fixed this way.
  - It is an explicit output change (FR-021, contract C-3), covered test-first by T058 and implemented by T060.
- **Alternatives considered**: Keep the bug. Rejected by the user's decision during analysis.

## R-15: Pre-existing constitution debt kept out of scope

- **VI (resolution hints)**: 38 of the 56 error messages in `commands/` have no `Hint:`. They are kept unchanged by FR-003 and will be resolved in follow-up feature 023-error-hints.
- **II (Pydantic contexts)**: factories pass `dict` contexts derived from validated models. This will be resolved in follow-up feature 024-typed-template-contexts.

Both are kept under the Constitution v2.1.0 "Pre-existing violations" governance clause and documented in the Complexity Tracking of `plan.md`. Before merge, T063 creates the follow-up spec directories.

## R-16: No shared `render_into()` helper

- **Decision**: The local `tpl()` helpers in `ep_agent.py`, `ep_generic.py` and `ep_restapi.py` stay as they are. Only their comments and docstrings are cleaned up. FR-013 is limited to single-entry registries and the duplicated `_tmpl()` helpers.
- **Rationale**: A shared `render_into(builder, path, template, ctx)` would be new code that accepts `dict` contexts. Under Governance v2.1.0, new code must comply with every principle, including II (Pydantic-validated contexts). The duplication it removes is small and local. The right fix belongs to 024-typed-template-contexts.
- **Alternatives considered**: `render_into` accepting only `BaseModel`. It would require new Pydantic context models for the entry-point factories, which is the scope of 024.
