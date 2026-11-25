# Contract: Generated Files for `--type psycopg`

**Feature**: 031-psycopg-adapter | **Date**: 2026-11-25

Exact files, dependencies, `conftest.py` changes and CLI behavior produced by `scaffold gda --type psycopg [--gateway <gw>] [--dry-run]`.

---

## File Tree

For a project named `my_app` (`python_package = "my_app"`):

```text
src/
├── my_app/
│   └── infrastructure/
│       └── driven_adapters/
│           └── psycopg/
│               ├── __init__.py
│               ├── psycopg_config.py
│               ├── psycopg_repository.py
│               └── psycopg_settings.py
└── tests/
    ├── conftest.py                       ← appended (idempotent)
    ├── application/config/test_wiring.py ← test appended only with --gateway
    └── infrastructure/
        └── driven_adapters/
            └── psycopg/
                └── test_psycopg_adapter.py
```

Dry-run baseline key `gda:psycopg` (sorted):

```json
[
  "src/my_app/infrastructure/driven_adapters/psycopg/__init__.py",
  "src/my_app/infrastructure/driven_adapters/psycopg/psycopg_config.py",
  "src/my_app/infrastructure/driven_adapters/psycopg/psycopg_repository.py",
  "src/my_app/infrastructure/driven_adapters/psycopg/psycopg_settings.py",
  "src/tests/conftest.py",
  "src/tests/infrastructure/driven_adapters/psycopg/test_psycopg_adapter.py"
]
```

---

## Dependencies Injected

### Runtime (`[project.dependencies]`)

| Package | Constant |
|---|---|
| `psycopg[binary]~=3.3.9` | `PSYCOPG_BINARY` (existing, shared with the sqlalchemy postgresql driver) |
| `psycopg-pool~=3.3.3` | `PSYCOPG_POOL` (new) |
| `pydantic-settings~=2.15.0` | `PYDANTIC_SETTINGS` (existing) |

No test-group or dev-group dependencies. Each package is injected as its own requirement; if `psycopg[binary]` already exists, only the missing packages are added.

---

## `conftest.py` Contract

### Added fixture

```python
@pytest.fixture(autouse=True)
def psycopg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSYCOPG_DATABASE_URL", "postgresql://user:password@localhost:5432/test")
```

- **Idempotency marker**: `psycopg_env`.
- The URL is a placeholder: the pool opens lazily, so no test connects to it.
- Written through `DrivenAdapterFactory.append_env_fixture`, so the shared header is added only when `conftest.py` does not yet contain `import pytest`.

### Removal

`scaffold dm --name psycopg --confirm` removes the `psycopg_env` block via `DeleteModuleFactory._remove_conftest_fixture` (entry `"psycopg": "psycopg_env"` in `_CONFTEST_FIXTURE_NAMES`); other fixtures are untouched.

---

## CLI Contract

| Invocation | Result |
|---|---|
| `scaffold gda --type psycopg` | Creates the tree above; prints `✓ Driven adapter psycopg created. Created N file(s).` |
| `scaffold gda --type psycopg --gateway book_repository` | Repository uses `@wireup.injectable(as_type=BookRepository)`; appends `test_container_resolves_psycopg`; re-syncs `MISSING_ADAPTERS` |
| `scaffold gda --type psycopg --gateway nope` | Exit 1, "Gateway 'nope' not found…" with hint |
| `scaffold gda --type psycopg --driver sqlite` | Exit 1, "--driver is only valid with --type sqlalchemy (got --type 'psycopg')." |
| `scaffold gda --type psycopg` (second time) | Exit 1, directory already exists; `conftest.py` unchanged |
| `scaffold gda --type psycopg --dry-run` | Prints tree and pending `[project.dependencies]`; writes nothing |
| `scaffold gda --help` | Lists `psycopg` with its description and an example |
