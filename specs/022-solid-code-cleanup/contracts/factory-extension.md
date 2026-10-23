# Contract: adding a new type without touching `commands/`

An internal contract for maintainers. `tests/factory/test_extensibility.py` verifies it.

## Entry point

1. Create `factory/entry_points/ep_<type>.py`:

   ```python
   class EntryPointFoo(EntryPointFactory):
       subdir: ClassVar[str] = "foo"
       supported_flags: ClassVar[frozenset[EntryPointFlag]] = frozenset({EntryPointFlag.ENABLE_KAFKA})
       conflicts: ClassVar[tuple[EntryPointConflict, ...]] = ()

       def build(self, builder: ModuleBuilder) -> None: ...
   ```

2. Register the factory with one line in `factory/entry_points/__init__.py`:

   ```python
   ENTRY_POINT_FACTORIES["foo"] = EntryPointFoo
   ```

3. Add its templates under `templates/entry_point/foo/` and their test under `tests/templates/`, as Constitution II requires.

With that, `gep --type foo` does the following with no further changes:

- validates flags with messages derived from the registered types (research R-02);
- applies the `conflicts` guards and the duplicate guard on `subdir`;
- shows `result_notes()`, which by default is the `main.py` replacement notice;
- registers the script if the factory called `builder.set_project_script(...)`.

## Driven adapter

- Inherit from `DrivenAdapterFactory`.
- Declare `fixed_name`, or `None` when `--name` provides the name.
- Register it in `factory/driven_adapters/__init__.py`.

## Pipeline

- Add a `PipelineFactory(output_path=…, template=…, display_name=…)` instance to `PIPELINE_PROVIDERS` in `factory/pipelines/__init__.py`.

## Guarantees

- An unknown `--type` produces `Unknown type '<x>'. Allowed: <registry keys in order>.`. An unknown `--provider` produces `Unknown provider '<x>'. Allowed: <registry keys in order>.`.
- No module in `commands/` contains type literals (`"restapi"`, `"mcp"`, `"github"`…). The exception is `add_mcp_tool.py`, which is MCP-specific by definition: it validates `--type mcp`.
