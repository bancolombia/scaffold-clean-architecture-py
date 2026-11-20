# Common errors after migrating

- **`WireupError: Parameter 'x' of F has an unknown dependency on G`**: no injectable provides `G`. Add `@wireup.injectable(as_type=G)` to the adapter, or generate one with `scaffold gda --gateway <g>`.
- **`WireupError: Multiple implementations registered for G`**: two classes declare `as_type=G`; keep one or add a qualifier.
- **`NameError: name 'Injected' is not defined`**: `Injected`/`Inject` imported under `TYPE_CHECKING`; import at runtime and keep ruff `TC` ignored.
- **`ModuleNotFoundError: No module named 'dependency_injector'`**: a module still imports the legacy package; run `scaffold up --dry-run --report json` to list what is left.
- **`test_wiring.py` XPASS (strict)**: `MISSING_ADAPTERS` lists a gateway that now has an adapter; remove it from the list.
- **`pydantic_core.ValidationError` at startup**: a settings field without default has no env var; set it in the environment or in `src/tests/conftest.py`.
- **`mypy: Unused "type: ignore" comment`** in 0.5.0 tests: delete the stale ignore.
