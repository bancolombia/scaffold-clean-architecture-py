---

description: "Task list for 022-solid-code-cleanup"
---

# Tasks: SOLID refactor and comment cleanup of the scaffolder

**Input**: Design documents in `specs/022-solid-code-cleanup/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required by Constitution V (test-first, non-negotiable) and FR-020. In every story, tests are written first and must fail. The exception is the US1 safety-net tests, which must pass from the start because they pin the current behavior.

**Organization**: Tasks are grouped by the user stories in the spec.

**Cross-cutting rule**: after every task that touches `src/`, run:
- `uv run pytest -q`
- `uv run ruff check src/ tests/`
- `uv run mypy src/`

The suite must stay green (baseline: 739 passed, 1 skipped, 96.50%).

**Conventions**:
- If `uv` fails with a TLS error, use `export SSL_CERT_FILE=/etc/ssl/cert.pem`.
- New comments and docstrings follow the Google style, are short and carry no Spec Kit IDs (research R-10).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no pending dependencies).
- **[Story]**: user story from the spec (US1–US6).

## Path Conventions

- Code: `src/scaffold_ca_python/`
- Tests: `tests/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Capture the reference and enable the guardrails without leaving the branch red.

- [x] T001 Capture the reference trees from `main` by following step 1 of `specs/022-solid-code-cleanup/quickstart.md`:
  - `/tmp/ref022.sha` (mcp + the other commands);
  - `/tmp/ref022-restapi.sha` (`ca --name demo-api` + `gep --type restapi` + `gda --type secrets`).

  In both, remove the `created_at` line from `pyproject.toml` before hashing.
- [x] T002 Enable the new rules in `pyproject.toml`:
  - `select = ["E", "F", "I", "UP", "ANN", "B", "SIM", "C90"]` and a `[tool.ruff.lint.mccabe]` section with `max-complexity = 10`;
  - a temporary `[tool.ruff.lint.per-file-ignores]` with `C901` for:
    - `src/scaffold_ca_python/commands/generate_entry_point.py`
    - `src/scaffold_ca_python/commands/generate_driven_adapter.py`
    - `src/scaffold_ca_python/core/file_writer.py`
    - `src/scaffold_ca_python/core/structure_validator.py`
    - `src/scaffold_ca_python/factory/simple/delete_module_factory.py`
  - the comment `# Temporary: removed by the end of feature 022.` above that block.
- [x] T003 [P] Fix B905 in `src/scaffold_ca_python/core/file_writer.py` with `zip(creates, staged, strict=True)`.
- [x] T004 [P] Fix the 2 B017 in `tests/`: replace `pytest.raises(Exception)` with the concrete exception the code raises. Find them with `uv run ruff check tests/ --select B017`.
- [x] T005 Fix the 2 B904 and the SIM108 in `src/scaffold_ca_python/commands/generate_entry_point.py`:
  - the `raise typer.Exit(code=1)` lines inside `except OSError` / `except SyntaxError`;
  - the `failed_file` `if/else`.

  This is a minimal patch; the full redesign is T049. Leave `uv run ruff check src/ tests/` green.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create the shared utilities used by US2, US4 and US6. **No** command is migrated in this phase.

**⚠️ CRITICAL**: No story that modifies commands may start before this phase and Phase 3 (safety net) are complete.

- [x] T006 Write `tests/commands/test_shared.py`. It must fail, because the module doesn't exist yet. It covers:
  - `fail()` prints `Error: <msg>`, prints `Hint: <hint>` only when given, and raises `typer.Exit` with `exit_code == 1`.
  - `require_project_root()` outside a project prints `"No scaffold-ca-python project found. Run 'scaffold ca' first."`.
  - `require_project_root(not_found_message=None)` prints the `ScaffoldError` text.
  - `ensure_absent()` prints `File '<rel>' already exists.` with `kind="File"` and `Directory '<rel>/' already exists.` with `kind="Directory"`. Both are followed by the given hint.
  - `print_dry_run_tree()` lists the paths sorted and relative to the base, under the title `<title> (dry run)`.
  - `print_pending_dependencies()` prints `Would add to [project.dependencies]: …` and one line per `[dependency-groups.<g>]` group.
- [x] T007 Implement `src/scaffold_ca_python/commands/_shared.py` according to research R-07. It exposes:
  - `console`
  - `fail(message: str, hint: str | None = None) -> NoReturn`
  - `require_project_root(not_found_message: str | None = PROJECT_NOT_FOUND) -> Path`
  - `validate_name_or_exit(name: str, validator: Callable[[str], None]) -> None`
  - `ensure_absent(path: Path, project_root: Path, *, kind: Literal["File", "Directory"], hint: str) -> None`
  - `print_dry_run_tree(title: str, paths: Iterable[Path], base: Path) -> None`
  - `print_pending_dependencies(builder: ModuleBuilder) -> None`
  - `build_and_persist(factory: ModuleFactory, builder: ModuleBuilder) -> list[Path]`
  - `dry_run_option(help: str = "Preview without writing.")`, which returns the `typer.Option` with `"--dry-run/--no-dry-run"`, `rich_help_panel="Options"` and `show_default=True`

  Makes T006 pass.

**Checkpoint**: `_shared.py` is tested and no command has changed yet.

---

## Phase 3: User Story 1 - CLI behavior intact (Priority: P1) 🎯 MVP

**Goal**: Pin the current observable behavior (messages, exit codes, files) with tests before refactoring.

**Independent Test**: `uv run pytest tests/commands/test_behavior_contract.py` passes **before and after** the refactor. The only assertions that change are those affected by the allowed changes C-1, C-2 and C-3. The T064 comparison shows no differences.

### Tests for User Story 1 ⚠️ (must pass immediately: they pin current behavior)

- [x] T008 [P] [US1] Create `tests/commands/test_behavior_contract.py` with parametrized `gep` cases, on a project created with `ca --name my-app` in `tmp_path`. Each case asserts the exact text after `strip_ansi` and `exit_code == 1`:
  - `--type x` → `Unknown type 'x'. Allowed: restapi, agent, mcp, generic.`
  - `--type mcp --swagger f.yaml` → `--swagger is only valid with --type restapi.`
  - `--type mcp --enable-mcp-client` → `--enable-mcp-client is not valid with --type mcp.`
  - `--type agent --with-prompts` → `--with-resources and --with-prompts are only valid with --type mcp.`
  - `restapi` after `mcp` → `Incompatible entry point 'mcp_server'` and `Remove '…' before adding restapi.`
  - `agent` after `restapi` → `Incompatible entry point 'restapi'` and `before adding agent.`
  - `mcp` twice → `Directory '…/mcp_server/' already exists.`
  - `--add-tool` without `--type` → `--add-tool is only valid with --type mcp.`
  - `--type mcp --add-tool --name x --enable-kafka` → `--add-tool is incompatible with --enable-kafka.`
- [x] T009 [P] [US1] Add to `tests/commands/test_behavior_contract.py` the `gda`, `gpipe`, `gm`, `guc`, `gh` and `dm` cases:
  - `gda --type generic` → `--name is required when --type is generic.`
  - `gda --type x` → `Unknown type 'x'. Allowed: rest-consumer, secrets, generic.`
  - `gpipe --provider x` → `Unknown provider 'x'. Allowed: github, azure.`
  - `gm --name order` twice → `File '…order.py' already exists.`
  - any command outside a project → `No scaffold-ca-python project found. Run 'scaffold ca' first.`
  - `dm --name nope` → `No module named 'nope' found in project.`
- [x] T010 [P] [US1] Add to `tests/commands/test_behavior_contract.py` the `gep` success and dry-run outputs:
  - `gep --type restapi --dry-run` contains `Would update : my_app = "my_app.server:start_server"`. This is the current output: Rich swallows `[project.scripts]`. T060 fixes it (C-3) and updates this assertion at that point.
  - `gep --type mcp` contains `main.py replaced with mcp entrypoint.`
  - `gep --type agent --dry-run` contains `main.py will be replaced with agent entrypoint.`
  - after `gep --type mcp`, `pyproject.toml` contains the script with `:main`.

**Checkpoint**: the safety net is green against the current code. From here, any refactor story can start.

---

## Phase 4: User Story 2 - Add a new type without touching the commands (Priority: P1)

**Goal**: Each type's knowledge lives in its factory, the registries live in `factory/`, and the script is registered explicitly (FR-007, FR-008, FR-009).

**Independent Test**: `uv run pytest tests/factory/test_extensibility.py` registers a complete fake factory, and `gep --type stub` uses it (subdir, flags, conflicts, notes) with no changes in `commands/`.

### Tests for User Story 2 ⚠️ (write first, must fail)

- [X] T011 [P] [US2] Rewrite `tests/factory/test_extensibility.py`:
  - **Factory `_StubFactory(EntryPointFactory)`**:
    - `subdir = "stub_ep"`;
    - `supported_flags = frozenset({EntryPointFlag.ENABLE_KAFKA})`;
    - `conflicts = (EntryPointConflict("restapi", "api"),)`;
    - registered with `monkeypatch.setitem(ENTRY_POINT_FACTORIES, "stub", _StubFactory)`.
  - **(a)** `gep --type stub --dry-run` calls `build()`, and the tree title is `stub_ep (dry run)`.
  - **(b)** `--type stub --swagger f.yaml` fails with `--swagger is only valid with --type restapi.`.
  - **(c)** If `infrastructure/entry_points/api` exists, it fails with `Incompatible entry point 'restapi'`.
  - **(d)** `main.py will be replaced with stub entrypoint.` is shown.
  - **(e)** Over `src/scaffold_ca_python/commands/*.py` (excluding `add_mcp_tool.py`), `grep` finds none of the literals `"restapi"`, `"agent"`, `"generic"`, `"rest-consumer"`, `"secrets"`, `"github"`, `"azure"`. The `"mcp"` literal may only appear in `add_mcp_tool.py`.
- [X] T012 [P] [US2] Add these tests to `tests/factory/test_module_builder.py`:
  - `set_project_script()` sets `pending_project_script == "start_server"`, and `set_project_script("main")` sets `"main"`;
  - `persist()` calls `update_project_scripts(root, ctx, "main")` in real mode and `dry_run_scripts_update` in dry-run (checked with `monkeypatch`);
  - without a `set_project_script` call, `[project.scripts]` is not touched.
- [X] T013 [P] [US2] Add `tests/factory/test_registry.py::test_factory_descriptors`, asserting the values in the [data-model.md](data-model.md) table:

  | Type | `subdir` | `supported_flags` | `conflicts` |
  |---|---|---|---|
  | `restapi` | `"api/v1"` | `{SWAGGER, ENABLE_MCP_CLIENT, ENABLE_KAFKA}` | labels `("mcp_server", "agent")` |
  | `mcp` | `"mcp_server"` | `{MCP_PRIMITIVES, ENABLE_KAFKA}` | `(("restapi", "api"),)` |
  | `agent` | `"agent"` | `{ENABLE_MCP_CLIENT, ENABLE_KAFKA}` | `(("restapi", "api"),)` |
  | `generic` | `"generic"` | `{ENABLE_MCP_CLIENT, ENABLE_KAFKA}` | `()` |

  It also asserts the driven adapters' `fixed_name` (`rest-consumer` → `"rest_consumer"`, `secrets` → `"secrets"`, `generic` → `None`) and that `PIPELINE_PROVIDERS` has the keys `["github", "azure"]` in that order.
- [X] T014 [P] [US2] Add an injection test (FR-014) to `tests/commands/test_generate_pipeline.py`. It must fail. Inside a project created with `ca`, it calls `_generate_pipeline_impl("github", dry_run=False, renderer=FakeRenderer(), writer=FakeWriter())` and checks that the injected dependencies are used.

### Implementation for User Story 2

- [X] T015 [US2] Add to `src/scaffold_ca_python/core/module_builder.py`:
  - the method `set_project_script(entry_fn: str = "start_server") -> None`;
  - the property `pending_project_script: str | None`.

  `persist()` uses this value instead of `_params["scripts_entry"]` / `_params["scripts_entry_fn"]`. Makes T012 pass.
- [X] T016 [US2] Replace the `add_param("scripts_entry", …)` and `add_param("scripts_entry_fn", …)` calls:
  - with `builder.set_project_script()` in `src/scaffold_ca_python/factory/entry_points/ep_restapi.py`;
  - with `builder.set_project_script("main")` in `src/scaffold_ca_python/factory/entry_points/ep_mcp.py`.

  Update `tests/factory/entry_points/test_ep_mcp.py` and `tests/factory/entry_points/test_ep_restapi.py` to check `pending_project_script` instead of `get_param("scripts_entry")` (research R-08).
- [X] T017 [US2] Create `src/scaffold_ca_python/factory/entry_points/base.py` with:
  - **`EntryPointFlag(Enum)`**, members in order `SWAGGER`, `ENABLE_MCP_CLIENT`, `MCP_PRIMITIVES`, `ENABLE_KAFKA`. Each has a `label` (`"--swagger"`, `"--enable-mcp-client"`, `"--with-resources and --with-prompts"`, `"--enable-kafka"`) and a `verb` (`"is"`, `"is"`, `"are"`, `"is"`).
  - **`EntryPointConflict(NamedTuple)`** with `label: str` and `subdir: str`.
  - **`EntryPointFactory(ABC)`** with:
    - `subdir: ClassVar[str]`
    - `supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset()`
    - `conflicts: ClassVar[tuple[EntryPointConflict, ...]] = ()`
    - the abstract `build(builder)`
    - `result_notes(project_root: Path, pkg: str, type_key: str, *, dry_run: bool) -> list[str]`. By default it returns `["[yellow]⚠[/yellow] main.py will be replaced with {type_key} entrypoint."]` in dry-run and `["[yellow]⚠[/yellow] main.py replaced with {type_key} entrypoint."]` in real mode.
- [X] T018 [US2] Make `EntryPointRestApi`, `EntryPointMcp`, `EntryPointAgent` and `EntryPointGeneric` (in `src/scaffold_ca_python/factory/entry_points/ep_*.py`) inherit from `EntryPointFactory` and declare the `ClassVar`s from the [data-model.md](data-model.md) table.

  `EntryPointRestApi.result_notes` reproduces the current text of `generate_entry_point.py` exactly, so this task does **not** apply the C-3 fix:
  - **Dry-run**: `[dim]Would delete: src/{pkg}/main.py[/dim]` if `main.py` exists, plus `[dim]Would update [project.scripts]: {pkg} = "{pkg}.server:start_server"[/dim]`.
  - **Real mode**: `[green]✓[/green] Deleted src/{pkg}/main.py` if it exists, plus `[green]✓[/green] Updated [project.scripts]: {pkg} = "{pkg}.server:start_server"`.

  Note: `result_notes` is evaluated **after** `persist()`, as today. In real mode, the `Deleted src/{pkg}/main.py` line therefore only appears if `main.py` still exists. In practice it never appears, because `persist()` has already deleted it. Keep that order so the output doesn't change (covered by T010). Record it as a possible bug for a later feature.
- [X] T019 [US2] Move the registry to `src/scaffold_ca_python/factory/entry_points/__init__.py` as `ENTRY_POINT_FACTORIES: dict[str, type[EntryPointFactory]]`, in the order `restapi`, `agent`, `mcp`, `generic`. Also create `src/scaffold_ca_python/commands/_entry_point_rules.py` with:
  - **`check_flags(type_key, factory, active_flags, registry)`**: derives the messages per research R-02. If exactly one registered type supports the flag, the message is `"{label} {verb} only valid with --type {single}."`; otherwise it is `"{label} {verb} not valid with --type {type_key}."`.
  - **`check_conflicts(…)`**: reproduces the current text, `Incompatible entry point '[bold]{label}[/bold]' already exists at: {rel}` + `Hint: A project may have only one entry-point type. Remove '{rel}' before adding {type_key}.`
- [X] T020 [US2] Rewrite the creation part of `src/scaffold_ca_python/commands/generate_entry_point.py` to use `ENTRY_POINT_FACTORIES`, `check_flags`, `check_conflicts`, `factory.subdir` and `factory.result_notes`. Remove the `if type_ == …` branches. Leave the `--add-tool` flow untouched; T049 handles it.
- [X] T021 [P] [US2] Create `src/scaffold_ca_python/factory/driven_adapters/base.py` with:
  - `DrivenAdapterFactory(ABC)`;
  - the `ClassVar` `fixed_name: ClassVar[str | None] = None`;
  - the method `module_name(name: str | None) -> str | None`, which returns `fixed_name or name`.

  The classes in `da_rest_consumer.py` (`fixed_name = "rest_consumer"`), `da_secrets.py` (`"secrets"`) and `da_generic.py` (`None`) inherit from it.
- [X] T022 [US2] Move the registry to `src/scaffold_ca_python/factory/driven_adapters/__init__.py` as `DRIVEN_ADAPTER_FACTORIES`, in the order `rest-consumer`, `secrets`, `generic`. Rewrite `src/scaffold_ca_python/commands/generate_driven_adapter.py` so that it:
  - validates the type;
  - fails with `--name is required when --type is {type_}.` when `module_name(name)` is `None`;
  - validates `name` when given;
  - computes `subdir = to_snake_case(module_name)`;
  - has no `if/elif` per type and no `assert`.

  Remove the `# noqa: ANN001`.
- [X] T023 [P] [US2] Create `src/scaffold_ca_python/factory/pipelines/__init__.py` and `src/scaffold_ca_python/factory/pipelines/pipeline_factory.py`:
  - **`PipelineFactory`**: a frozen dataclass with `output_path: PurePosixPath`, `template: str`, `display_name: str`, and a `build(builder)` method that does `builder.add_file(project_root / output_path, builder.render(template, project_ctx), template_name=template)`.
  - **`PIPELINE_PROVIDERS`**:
    ```python
    {
        "github": PipelineFactory(PurePosixPath(".github/workflows/ci.yml"), "pipeline/github/ci.yml.jinja2", "ci.yml"),
        "azure": PipelineFactory(PurePosixPath("azure-pipelines.yml"), "pipeline/azure/azure_pipelines.yml.jinja2", "azure-pipelines.yml"),
    }
    ```
- [X] T024 [US2] Rewrite `src/scaffold_ca_python/commands/generate_pipeline.py`:
  - it uses `PIPELINE_PROVIDERS`, `ModuleBuilder` and `_shared`;
  - the signature is `_generate_pipeline_impl(provider: str | None, dry_run: bool, *, renderer: TemplateRenderer | None = None, writer: FileWriter | None = None)`, and both are passed to `ModuleBuilder(file_writer=writer, template_renderer=renderer)`. This makes T014 pass;
  - the `Allowed:` message comes from the registry keys;
  - remove the `renderer`/`writer` singletons, `_tmpl()`, `_PROVIDER_DEFAULT` and `_ALLOWED_PROVIDERS`;
  - keep the local `_load_project_context` until T031, unless T031 is already done (then use `load_project_context`).

  The duplicate message stays unchanged in this task; T059 changes it.
- [X] T025 [US2] Update `tests/factory/test_registry.py` and `tests/factory/test_dry_run_parity.py` to import `ENTRY_POINT_FACTORIES` / `DRIVEN_ADAPTER_FACTORIES` instead of `generate_entry_point._REGISTRY` / `generate_driven_adapter._REGISTRY` (research R-08). Confirm that T008–T014 and the full suite pass.

**Checkpoint**: US2 is complete, `commands/` has no type literals, and T011 is green.

---

## Phase 5: User Story 3 - Unified and correct project context (Priority: P2)

**Goal**: A single `load_project_context` for every command (FR-010, FR-011), with a regression test written first (FR-020).

**Independent Test**: `uv run pytest tests/core/test_project_context.py`.

### Tests for User Story 3 ⚠️ (write first, must fail)

- [X] T026 [P] [US3] Create `tests/core/test_project_context.py` with these `load_project_context` cases:
  - **(a)** With `[tool.scaffold-ca-python] name = "my-app"`, it returns `name == "my-app"` and `python_package == "my_app"`.
  - **(b)** Without that section, in a `demo_dir` directory, it returns `name == "demo_dir"`.
  - **(c)** With `[project].name = "other-name"` and `[tool.scaffold-ca-python].name = "my-app"`, it uses `my-app`.
- [X] T027 [P] [US3] Add an integration regression test to `tests/core/test_project_context.py`. Start from `ca --name my-app` and edit `[project].name = "renamed"` in `pyproject.toml`. Then:
  - `gep --type generic --dry-run` and `gm --name order --dry-run` show paths under `src/my_app/`. Today gep would use `src/renamed/`.
  - `gep --type mcp` followed by `gep --type mcp --add-tool --name ping` finds `src/my_app/infrastructure/entry_points/mcp_server/tools.py`.

### Implementation for User Story 3

- [X] T028 [US3] Implement `load_project_context(root: Path) -> ProjectContext` in `src/scaffold_ca_python/core/project_detector.py`. It reads `[tool.scaffold-ca-python].name` and falls back to `root.name`. Makes T026 pass.
- [X] T029 [US3] Replace the local `_load_project_context` with `load_project_context` in `src/scaffold_ca_python/commands/generate_entry_point.py`, the copy that reads `[project].name` today. Also remove the `to_snake_case` import if it becomes unused. Makes T027 pass.
- [X] T030 [P] [US3] Replace `_load_project_context` with `load_project_context` and delete the local copy, along with any `tomllib`/`ProjectContext` imports left unused, in:
  - `src/scaffold_ca_python/commands/generate_model.py`
  - `src/scaffold_ca_python/commands/generate_use_case.py`
  - `src/scaffold_ca_python/commands/generate_helper.py`
- [X] T031 [P] [US3] Do the same as T030 in:
  - `src/scaffold_ca_python/commands/generate_driven_adapter.py`
  - `src/scaffold_ca_python/commands/generate_pipeline.py`
  - `src/scaffold_ca_python/commands/delete_module.py`
- [X] T032 [US3] Check that `grep -rn "_load_project_context\|def load_project_context" src/` returns a single line (SC-004).

**Checkpoint**: US3 is complete, with T026 and T027 green.

---

## Phase 6: User Story 4 - Readable code with separated responsibilities (Priority: P2)

**Goal**: Single-responsibility functions with complexity ≤ 10, typed options, shared utilities in every command, and injected dependencies (FR-005, FR-006, FR-012, FR-013, FR-014).

**Independent Test**: `uv run ruff check src/ --select C90` passes **without** the temporary `per-file-ignores`, and the suite is green.

### Tests for User Story 4 ⚠️ (write first, must fail)

- [X] T033 [P] [US4] Create `tests/models/test_options.py` for `EntryPointOptions`:
  - it is frozen: assigning a field raises `FrozenInstanceError`;
  - `creation_flags()` returns `["--swagger", "--enable-kafka", "--enable-mcp-client", "--with-resources", "--with-prompts"]`, filtered to the active ones, in that order;
  - `apply_to(builder, routes)` leaves `routes`, `enable_kafka`, `enable_mcp_client`, `with_resources` and `with_prompts` in the builder.
- [X] T034 [P] [US4] Create `tests/core/test_openapi_routes.py` for `parse_routes(path)`. Move the `_parse_swagger` cases if they exist in `tests/commands/test_generate_entry_point.py`, and add:
  - YAML with `get`/`post` → `[("/x", "get"), ("/x", "post")]`;
  - JSON;
  - a non-dict root → `[]`;
  - non-dict `paths` → `[]`;
  - non-HTTP methods ignored (`parameters`).
- [X] T035 [P] [US4] Create `tests/core/test_module_locator.py` for `find_module_targets(project_root, pkg, snake)`:
  - a model with its test returns `[(src, test)]`;
  - an adapter without a test returns `[(dir, None)]`;
  - no match returns `[]`;
  - the search order is model, usecase, driven_adapters, entry_points, helpers.
- [X] T036 [P] [US4] Add a test to `tests/commands/test_generate_project.py` that calls `_generate_project_impl(name, dry_run=False, renderer=FakeRenderer(), writer=FakeWriter())` and checks that the injected dependencies are used, with no module-level singletons (FR-014).
- [X] T037 [P] [US4] Add two tests to `tests/templates/test_project_templates.py`. They must fail:
  - `project/package_init.py.jinja2` rendered with `{"name": "my-app"}` produces exactly `'"""my-app package."""\n'`;
  - `project/empty.jinja2` produces `""`.

  This satisfies Constitution II for the two files that don't come from a template today (FR-004 allows adding templates).
- [X] T038 [P] [US4] Add these cases to `tests/core/test_file_writer.py`:
  - a `FileExistsError` during pre-validation leaves no partial files;
  - deletes happen after creates;
  - inserts and appends are applied in declaration order.

  They pin the behavior before `_commit` is split. If equivalent tests already exist, note it and skip them.

### Implementation for User Story 4

- [X] T039 [P] [US4] Create `src/scaffold_ca_python/models/options.py` with `EntryPointOptions`, a `@dataclass(frozen=True, slots=True)` with these fields:
  - `type_: str`
  - `swagger: str | None = None`
  - `enable_kafka: bool = False`
  - `enable_mcp_client: bool = False`
  - `with_resources: bool = False`
  - `with_prompts: bool = False`
  - `add_tool: bool = False`
  - `name: str | None = None`
  - `params: tuple[str, ...] = ()`
  - `returns: str = "str"`
  - `description: str | None = None`
  - `dry_run: bool = False`

  Implement `creation_flags()` and `apply_to(builder, routes)`. Makes T033 pass.
- [X] T040 [P] [US4] Create `src/scaffold_ca_python/core/openapi_routes.py` with `parse_routes(path: Path) -> list[tuple[str, str]]`. Move `_parse_swagger` there from `generate_entry_point.py` and use a `_HTTP_METHODS` `frozenset`. Makes T034 pass.
- [X] T041 [P] [US4] Create `src/scaffold_ca_python/core/module_locator.py` with `find_module_targets(...)`, using the code that lives in `commands/delete_module.py::_find_module_targets` today. Express the 5 candidates as a `(layer_subpath, is_file)` table to lower complexity. Makes T035 pass.
- [X] T042 [US4] Make `src/scaffold_ca_python/commands/delete_module.py` and `src/scaffold_ca_python/factory/simple/delete_module_factory.py` use `find_module_targets`:
  - remove the local copy and the single-entry `_REGISTRY`, and instantiate `DeleteModuleFactory()` directly;
  - the preview uses a `_display(path, root)` helper (`relative_to` with fallback) instead of the two try/except blocks;
  - `DeleteModuleFactory.build` must end up with complexity ≤ 10.
- [X] T043 [P] [US4] Migrate `src/scaffold_ca_python/commands/generate_model.py` to `_shared`:
  - use `validate_name_or_exit`, `require_project_root`, `ensure_absent(kind="File", hint="Choose a different name or remove the existing file first.")`, `build_and_persist(ModelFactory(), builder)`, `print_dry_run_tree` and `dry_run_option()`;
  - remove the single-entry `_REGISTRY`.
- [X] T044 [P] [US4] Migrate two more commands the same way as T043, removing the single-entry `_REGISTRY` in both:
  - `src/scaffold_ca_python/commands/generate_use_case.py`, with factory `UseCaseFactory`;
  - `src/scaffold_ca_python/commands/generate_helper.py`, with factory `HelperFactory` and `ensure_absent(kind="Directory", hint="Choose a different name or remove the existing directory first.")`.
- [X] T045 [P] [US4] Migrate `src/scaffold_ca_python/commands/validate_structure.py` and `src/scaffold_ca_python/commands/update_project.py` to `require_project_root` and `dry_run_option(help=...)`, keeping their current help texts. In `update_project.py`, extract `_run_uv(cmd: list[str], cwd: Path, failure_message: str) -> None`. It keeps the current texts and exit codes: 1 when `uv` is missing, 2 on `CalledProcessError`.
- [ ] T046 [US4] Migrate `src/scaffold_ca_python/commands/generate_driven_adapter.py` to `_shared` (`print_dry_run_tree`, `print_pending_dependencies`, `ensure_absent(kind="Directory", ...)`, `build_and_persist`) and remove its C901 `per-file-ignores` from `pyproject.toml`.
- [ ] T047 [US4] Rewrite `src/scaffold_ca_python/commands/generate_project.py`:
  - **`_ROOT_FILES: tuple[tuple[str, str], ...]`**: the 7 root files (`pyproject.toml`, `README.md`, `.gitignore`, `mypy.ini`, `Dockerfile`, `.dockerignore`, `.python-version`) with their templates.
  - **`_DI_CONFIG_FILES`**: the 6 files in `application/config/`.
  - **Builder**: `ModuleBuilder(project_root=target_dir, ..., file_writer=writer, template_renderer=renderer)`, with `writer`/`renderer` as optional parameters of `_generate_project_impl`.
  - **Removed**: the singletons, `_add` and `_tmpl`. The signature becomes `name: str | None = None`, with no `type: ignore`.
  - **New templates**:
    - `src/scaffold_ca_python/templates/project/package_init.py.jinja2`: `"""{{ name }} package."""` followed by a newline;
    - `src/scaffold_ca_python/templates/project/empty.jinja2`: empty.

    They generate the package `__init__.py` and `src/tests/__init__.py` with byte-for-byte identical output.
  - **Kept**: the dry-run title `{python_pkg}/`, relative to `target_dir`, and the messages.

  Makes T036 and T037 pass.
- [ ] T048 [US4] Split `_generate_entry_point_impl` in `src/scaffold_ca_python/commands/generate_entry_point.py`. `register()` builds `EntryPointOptions` and calls `_generate_entry_point(options)`, which only orchestrates these functions:
  - `_resolve_factory(options)`
  - `_check_flags(...)`
  - `_load_routes(options.swagger)`, which uses `parse_routes` and the error `Swagger file '…' not found.`
  - `require_project_root()`
  - `_check_conflicts(...)`
  - `ensure_absent(...)`
  - `_build(...)`
  - `_report(...)`

  No function exceeds 5 parameters (SC-006) or complexity 10.
- [ ] T049 [US4] Extract the `--add-tool` flow to `src/scaffold_ca_python/commands/add_mcp_tool.py`, with the public function `add_mcp_tool(options: EntryPointOptions) -> None`. It orchestrates these steps:
  - `_check_add_tool_flags(options)`: incompatibilities and `--type mcp`.
  - `_build_spec(options)`.
  - `_resolve_paths(project_root, ctx)`: returns `tools.py` and `test_tools.py`.
  - `_read_sources(paths)`.
  - `_check_structure(sources, spec)`: `bind_tools`, the test structure, duplicate or reserved names, and the safety `ast.parse`. A `_TEST_TOOLS_STRUCTURE_ERROR` constant replaces the duplicated message.
  - `_check_writable(paths, project_root)`: `os.access`, with a module-level `import os`.
  - `_persist_with_restore(builder, originals)`: identifies the failed file through `OSError.filename`, defaulting to `tools.py` (research R-09). It keeps the text `Failed to write {file} ({e}). tools.py was restored; no changes were made.`.
  - `_report(...)`.

  Then:
  - use `require_project_root(not_found_message=None)` to keep the current detailed message;
  - make `generate_entry_point.py` delegate to `add_mcp_tool` only when `options.add_tool` is set;
  - remove the C901 `per-file-ignores` for `generate_entry_point.py`.
- [ ] T050 [P] [US4] Split `FileWriter._commit` in `src/scaffold_ca_python/core/file_writer.py` into:
  - `_partition(operations)`
  - `_stage(creates, tmpdir)`
  - `_preflight(creates, staged)`
  - `_apply_deletes(deletes)`
  - `_apply_mutations(operations)` (inserts and appends, in order)

  Also remove the empty `if TYPE_CHECKING: pass` and its import, and remove its C901 `per-file-ignores`. T038 must stay green.
- [ ] T051 [P] [US4] Split `StructureValidator.validate` in `src/scaffold_ca_python/core/structure_validator.py` into:
  - `_classify(py_file, src) -> tuple[str, Layer] | None`
  - `_parse(py_file) -> ast.Module | None`, with the warning and a module-level `import warnings`
  - `_violations_in(tree, py_file, python_package, source_layer) -> list[Violation]`

  Remove its C901 `per-file-ignores`. `tests/core/test_structure_validator.py` must stay green.
- [ ] T052 [US4] Check that `pyproject.toml` no longer has any C901 `per-file-ignores` and that `uv run ruff check src/ tests/` passes (SC-002). With `grep`, check that `src/scaffold_ca_python/commands/` has no `Tree(`, no `typer.Option("--dry-run` and no `find_project_root()` outside `_shared.py` (SC-004, FR-012).

**Checkpoint**: US4 is complete, with complexity ≤ 10 across `src/`.

---

## Phase 7: User Story 5 - Precise, noise-free comments (Priority: P3)

**Goal**: Short Google-style docstrings and zero Spec Kit ID references (FR-015).

**Independent Test**: `grep -rnE '\b(T0[0-9]{2}|FR-[0-9]{3}|US-?[0-9]|R-[0-9]{2})\b|Phase [0-9]' src/ | grep '\.py:'` returns 0 lines.

### Tests for User Story 5 ⚠️

- [ ] T053 [P] [US5] Create `tests/test_source_hygiene.py`. It must fail today. It walks `src/scaffold_ca_python/**/*.py`, excluding `templates/`, and asserts:
  - no matches for the regex `\b(T0\d{2}|FR-\d{3}|US-?\d|R-\d{2})\b|Phase \d`;
  - no lines starting with `# ---`.

### Implementation for User Story 5

- [ ] T054 [P] [US5] Clean up `src/scaffold_ca_python/commands/*.py`:
  - remove the `(Txxx)` suffix from module docstrings;
  - remove comments that repeat the next line (`# --- Validate name ---`, `# Get factory class and instantiate`, `# Invoke factory…`, `# Persist all operations`);
  - remove banners;
  - remove the comment `# Both names route to the same handler…` if it adds nothing.

  The docstrings of the `_impl` functions and of the commands become one line stating what and why.
- [ ] T055 [P] [US5] Clean up `src/scaffold_ca_python/core/*.py` and `src/scaffold_ca_python/models/*.py`:
  - convert the NumPy-style docstrings (underlined `Parameters`/`Returns`/`Raises`) in `module_builder.py`, `file_writer.py`, `project_detector.py` and `template_renderer.py` to Google style, with `Args:`/`Returns:`/`Raises:` only when they add something the signature doesn't say;
  - in `mcp_tool_spec.py`, remove `Args:` entries that just repeat the parameter name;
  - remove `(R-10)`, `(T0xx)`, banners and comments that merely paraphrase the code (in `file_writer.py`: `# File exists - normalize…`, `# Strip all trailing newlines…`).
- [ ] T056 [P] [US5] Clean up `src/scaffold_ca_python/factory/**/*.py`:
  - `build()` docstrings become one line, with no lists of files or dependency versions;
  - remove `# Phase 4 / T025`, `# Phase 5 / T031`, `# Always-generated files`, `# Dependencies` and similar;
  - keep comments that explain why, such as the `mcp~=1.30.0` cap.

  The local `tpl()` helpers stay (research R-16); only their comments are cleaned up. Makes T053 pass.

**Checkpoint**: US5 is complete.

---

## Phase 8: User Story 6 - Minor cleanup, output fixes and guardrails (Priority: P3)

**Goal**: A correct `gpipe` message, `[project.scripts]` shown literally, no dead code or causeless `from None`, consistent typing, and final guardrails (FR-016, FR-017, FR-018, FR-021).

**Independent Test**:
- Run `gpipe --provider github` twice: the second error does not mention `--force`.
- `gep --type restapi --dry-run` shows `[project.scripts]`.
- `ruff check` is green with no temporary ignores.

### Tests for User Story 6 ⚠️ (write first, must fail)

- [ ] T057 [P] [US6] Add a test to `tests/commands/test_generate_pipeline.py` that runs `gpipe --provider github` twice and asserts:
  - the output contains `'ci.yml' already exists at '.github/workflows/ci.yml'.`;
  - it contains `Hint: Remove the existing file first or choose a different provider.`;
  - it does **not** contain `--force`;
  - `exit_code == 1`.
- [ ] T058 [P] [US6] Add the C-3/FR-021 test to `tests/commands/test_behavior_contract.py`. It must fail. It asserts that:
  - `gep --type restapi --dry-run` contains `Would update [project.scripts]: my_app = "my_app.server:start_server"`;
  - `gep --type restapi` contains `Updated [project.scripts]: my_app = "my_app.server:start_server"`.

  See `contracts/cli-behavior.md` C-3.

### Implementation for User Story 6

- [ ] T059 [US6] Remove `Use --force to overwrite.` from the duplicate message in `src/scaffold_ca_python/commands/generate_pipeline.py`, using `ensure_absent` or `fail(...)` with the current hint. Makes T057 pass. If the final text differs, also update C-2 in `specs/022-solid-code-cleanup/contracts/cli-behavior.md`.
- [ ] T060 [US6] In `EntryPointRestApi.result_notes` (`src/scaffold_ca_python/factory/entry_points/ep_restapi.py`), pass `[project.scripts]` through `rich.markup.escape()` in both the dry-run and the real-mode line. Update the T010 assertion to the C-3 text. Makes T058 pass.
- [ ] T061 [US6] Final FR-017 sweep over `src/`, with `grep`:
  - replace `raise typer.Exit(code=1) from None` outside an `except` with `fail(...)` or `raise typer.Exit(code=1)`;
  - no unjustified `# noqa` remains;
  - no control-flow `assert` remains;
  - no `= None  # type: ignore[assignment]` remains;
  - no `_PROVIDER_DEFAULT` remains.

  Record the result of each `grep` in the commit.

**Checkpoint**: US6 is complete.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T062 [P] Update the extension docs in `README.md`, if there is a section about adding types, to point to `factory/*/__init__.py` and `specs/022-solid-code-cleanup/contracts/factory-extension.md`.
- [ ] T063 [P] Create the follow-up spec directories required by Constitution v2.1.0 ("Pre-existing violations" clause, point 3), each with an initial `spec.md` describing the debt measured in the `plan.md` Complexity Tracking:
  - `specs/023-error-hints/` (38 messages without `Hint:`);
  - `specs/024-typed-template-contexts/` (`dict` template contexts; includes the typed `build(builder, options)` idea from research R-05 and the shared `render_into` helper from R-16).
- [ ] T064 Run the full validation in `specs/022-solid-code-cleanup/quickstart.md`:
  - **Step 1**: regenerate the trees in `/tmp/new022` and `/tmp/new022-restapi` and `diff` them against T001. An empty diff is expected: C-1 does not apply to unedited projects, and C-2/C-3 only affect console output.
  - **Templates (FR-004)**: `git diff --stat main -- src/scaffold_ca_python/templates` shows only the 2 new files from T047 (`package_init.py.jinja2` and `empty.jinja2`), with no changes to existing templates.
  - **Steps 2 to 5**: full suite, `ruff`, `mypy`, the measurable criteria, the allowed changes and extensibility.

  Record the results (test count and coverage) in the PR description.
- [ ] T065 Run `uv run pytest tests/commands/test_performance.py` and compare with `main` (no regression above 10%).
- [ ] T066 Mark every task as completed and confirm that `.specify/feature.json` points to `specs/022-solid-code-cleanup`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T001 must run from `main` or before any change in `src/`.
- **Foundational (Phase 2)**: depends on Setup.
- **US1 (Phase 3)**: depends on Setup. It **blocks** every story that modifies commands (US2–US6).
- **US2 (Phase 4)**: depends on Foundational and US1.
- **US3 (Phase 5)**: depends on US1. It is independent of US2, except T031, which touches `generate_pipeline.py` like T024; run those two in sequence.
- **US4 (Phase 6)**: depends on Foundational, US1 and US2, because T048 and T049 rewrite `generate_entry_point.py` on top of the US2 design. T042–T045 only need Foundational.
- **US5 (Phase 7)**: best done after US4, to avoid cleaning code that gets rewritten later.
- **US6 (Phase 8)**:
  - T057 and T059 depend on T024.
  - T058 and T060 depend on T018; T060 deliberately changes the output pinned by T010 (C-3).
  - T061 goes last.
- **Polish (Phase 9)**: depends on everything. T063 must be done before merge.

### User Story Dependencies

```text
Setup ─► Foundational ─┬─► US1 ─┬─► US2 ─► US4 ─► US5 ─► US6 ─► Polish
                       │        └─► US3 ────────────┘
                       └──────────────► (US4 tasks T042–T045)
```

### Within Each User Story

- Tests come first and must fail, except the US1 tests, which must pass.
- Then come models and descriptors, then the registry and rules, then the commands, and finally verification.
- Every task ends with a green suite and can be its own commit.

### Parallel Opportunities

- **Setup**: T003 and T004.
- **US1**: T008, T009 and T010 touch the same file. They can be written in parallel if split into `test_behavior_contract_gep.py` and `test_behavior_contract_misc.py`; otherwise, run them in sequence.
- **US2**: tests T011–T014, and tasks T021 and T023 (different factory packages).
- **US3**: T026 and T027, then T030 and T031.
- **US4**: tests T033–T038, tasks T039–T041, migrations T043–T045, and T050–T051.
- **US5**: T054, T055 and T056.
- **US6**: T057 and T058.
- **Polish**: T062 and T063.

---

## Parallel Example: User Story 4

```bash
# Tests first (all in different files):
Task: "T033 tests/models/test_options.py"
Task: "T034 tests/core/test_openapi_routes.py"
Task: "T035 tests/core/test_module_locator.py"
Task: "T036 tests/commands/test_generate_project.py (injection)"
Task: "T037 tests/templates/test_project_templates.py (new templates)"

# Independent implementations:
Task: "T039 src/scaffold_ca_python/models/options.py"
Task: "T040 src/scaffold_ca_python/core/openapi_routes.py"
Task: "T041 src/scaffold_ca_python/core/module_locator.py"

# Core splits with no dependencies between them:
Task: "T050 core/file_writer.py"
Task: "T051 core/structure_validator.py"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup), with the reference captured and the guardrail enabled.
2. Phase 2 (Foundational): `_shared.py` tested.
3. Phase 3 (US1): the behavior safety net is green.
4. **STOP and VALIDATE**: at this point the branch protects the current behavior, and any later refactor is safe.

### Incremental Delivery

1. **US2**: extensibility, the main SOLID benefit (open/closed).
2. **US3**: the context fix, small and high-value.
3. **US4**: SRP, DRY and complexity. It is the largest phase and is split into many commits.
4. **US5 and US6**: comment cleanup, output fixes and final guardrails.
5. **Polish**: follow-up specs, tree comparison and the PR.

### Notes

- If an existing test fails because of an unplanned **text** change, fix the code, not the test (FR-003). The only tests that change are those listed in research R-08 and those for C-1, C-2 and C-3.
- `D` (pydocstyle) is not enabled; it is out of scope by the user's decision.
