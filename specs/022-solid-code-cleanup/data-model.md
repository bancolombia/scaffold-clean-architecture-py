# Data Model: SOLID refactor and comment cleanup

Internal entities that the refactor introduces or modifies. There is no new persistence: the only persisted state is still the generated project and its `pyproject.toml`.

## ProjectContext (modified: how it is loaded)

| Field | Type | Source |
|---|---|---|
| `name` | `str` (validated by `NAME_RE`) | `[tool.scaffold-ca-python].name`; if missing, the root directory name |
| `python_package` | `str` (computed) | `to_snake_case(name)` |
| `python_package_script` | `str` (computed) | `to_kebab_case(name)` |

- **Single loader**: `core.project_detector.load_project_context(root: Path) -> ProjectContext`.
- **FR-011 rule**: `python_package` stays in snake_case. The code `gep` generates does not change for projects created with the tool, because in those `[project].name == [tool.scaffold-ca-python].name`.
- **Behavior change (FR-010)**: `gep` and `--add-tool` stop reading `[project].name`.

## EntryPointOptions (new, `models/options.py`)

Dataclass with `frozen=True, slots=True`. Groups the 12 parameters of `gep`.

| Field | Type | Default |
|---|---|---|
| `type_` | `str` | — |
| `swagger` | `str \| None` | `None` |
| `enable_kafka` | `bool` | `False` |
| `enable_mcp_client` | `bool` | `False` |
| `with_resources` | `bool` | `False` |
| `with_prompts` | `bool` | `False` |
| `add_tool` | `bool` | `False` |
| `name` | `str \| None` | `None` |
| `params` | `tuple[str, ...]` | `()` |
| `returns` | `str` | `"str"` |
| `description` | `str \| None` | `None` |
| `dry_run` | `bool` | `False` |

Methods:
- `creation_flags() -> list[str]`: returns the active creation flags, in the current order (`--swagger`, `--enable-kafka`, `--enable-mcp-client`, `--with-resources`, `--with-prompts`). The `--add-tool` guard uses it.
- `apply_to(builder, routes) -> None`: transfers the build parameters to the builder (see research R-05).

## EntryPointFlag (new, enum in `factory/entry_points/base.py`)

| Member | Label in messages | Verb | Active when |
|---|---|---|---|
| `SWAGGER` | `--swagger` | `is` | `options.swagger` is truthy |
| `ENABLE_MCP_CLIENT` | `--enable-mcp-client` | `is` | `options.enable_mcp_client` |
| `MCP_PRIMITIVES` | `--with-resources and --with-prompts` | `are` | `with_resources or with_prompts` |
| `ENABLE_KAFKA` | `--enable-kafka` | `is` | `options.enable_kafka` |

The command evaluates the flags in table order. Research R-02 describes how the message is derived.

## EntryPointConflict (new)

A named tuple `(label: str, subdir: str)`: a directory under `infrastructure/entry_points/` whose existence prevents creating the type.

## EntryPointFactory (new, ABC implementing `ModuleFactory`)

| Member | Type | Default |
|---|---|---|
| `subdir` | `ClassVar[str]` | required |
| `supported_flags` | `ClassVar[frozenset[EntryPointFlag]]` | `frozenset()` |
| `conflicts` | `ClassVar[tuple[EntryPointConflict, ...]]` | `()` |
| `build(builder)` | abstract | — |
| `result_notes(project_root, pkg, type_key, *, dry_run)` | `list[str]` | `main.py` replacement notice |

Declared values, equivalent to the current logic:

| Type | subdir | supported_flags | conflicts | result_notes |
|---|---|---|---|---|
| `restapi` | `api/v1` | SWAGGER, ENABLE_MCP_CLIENT, ENABLE_KAFKA | `mcp_server`, `agent` | override: `main.py` deletion + `[project.scripts]` (escaped, C-3) |
| `mcp` | `mcp_server` | MCP_PRIMITIVES, ENABLE_KAFKA | `restapi`→`api` | default |
| `agent` | `agent` | ENABLE_MCP_CLIENT, ENABLE_KAFKA | `restapi`→`api` | default |
| `generic` | `generic` | ENABLE_MCP_CLIENT, ENABLE_KAFKA | — | default |

Note: today `--enable-kafka` and `--enable-mcp-client` are accepted without error by types that don't use them. Declaring them as supported keeps that behavior.

## DrivenAdapterFactory (new, ABC)

| Member | Type | Meaning |
|---|---|---|
| `fixed_name` | `ClassVar[str \| None]` | when set, `--name` is ignored (`rest_consumer`, `secrets`) |
| `module_name(name: str \| None) -> str \| None` | method | returns `fixed_name or name`. When the result is `None`, the command fails with `"--name is required when --type is {type}."` |

The subdirectory is `to_snake_case(module_name)`.

## PipelineFactory (new, `factory/pipelines/`)

| Field | Type | github | azure |
|---|---|---|---|
| `output_path` | relative `PurePosixPath` | `.github/workflows/ci.yml` | `azure-pipelines.yml` |
| `template` | `str` | `pipeline/github/ci.yml.jinja2` | `pipeline/azure/azure_pipelines.yml.jinja2` |
| `display_name` | `str` | `ci.yml` | `azure-pipelines.yml` |

`PIPELINE_PROVIDERS: dict[str, PipelineFactory]` keeps the `github, azure` order for the `Allowed: …` message. `build()` renders with the `ProjectContext` (a Pydantic model), so it complies with Constitution II.

## ModuleBuilder (modified)

| Change | Detail |
|---|---|
| + `set_project_script(entry_fn: str = "start_server")` | replaces `add_param("scripts_entry"/"scripts_entry_fn")` |
| + `pending_project_script: str \| None` (property) | what tests and dry-run output read |
| `persist()` | applies dependencies, groups and the script; no longer reads magic keys from `_params` |
| `add_param`/`get_param` | kept for build flags (R-05) |

## ModuleTarget (new, `core/module_locator.py`)

`find_module_targets(project_root, pkg, snake) -> list[tuple[Path, Path | None]]`. A single implementation, shared by `delete_module` (preview) and `DeleteModuleFactory` (deletion).

## Internal utilities (stateless)

- `commands/_shared.py`: see research R-07.
- `commands/_entry_point_rules.py`: `check_flags()`, `check_conflicts()` (research R-02/R-03).
- New templates: `project/package_init.py.jinja2`, `project/empty.jinja2` (research R-13).
