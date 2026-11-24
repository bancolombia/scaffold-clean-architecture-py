# Contract: Generated Files for `--type sqlalchemy`

**Feature**: 030-sqlalchemy-adapter | **Date**: 2026-11-23

This document defines the exact set of files, dependencies, and `conftest.py` changes produced by `scaffold gda --type sqlalchemy [--gateway <gw>] [--driver postgresql|sqlite]`.

---

## File Tree

For a project named `my_app` (`python_package = "my_app"`):

```
src/
├── my_app/
│   └── infrastructure/
│       └── driven_adapters/
│           └── sqlalchemy/
│               ├── __init__.py
│               ├── sqlalchemy_config.py
│               ├── sqlalchemy_models.py       ← new in 030
│               ├── sqlalchemy_repository.py
│               └── sqlalchemy_settings.py
└── tests/
    ├── conftest.py                            ← appended (idempotent)
    └── infrastructure/
        └── driven_adapters/
            └── sqlalchemy/
                └── test_sqlalchemy_adapter.py
```

Dry-run baseline key: `gda:sqlalchemy`.

---

## Dependencies Injected

### Runtime (`[project.dependencies]`)

| Driver | Package |
|--------|---------|
| `postgresql` (default) | `psycopg[binary]~=3.2.0` |
| `sqlite` | `aiosqlite~=0.22.1` |
| Both drivers | `sqlalchemy[asyncio]~=2.1.8` |
| Both drivers | `pydantic-settings~=2.15.0` |

### Test group (`[dependency-groups.test]`)

| Package | Always? |
|---------|---------|
| `aiosqlite~=0.22.1` | Yes — in-memory SQLite for all generated project tests |

---

## `conftest.py` Contract

### Added fixture

```python
@pytest.fixture(autouse=True)
def sqlalchemy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
```

**Idempotency marker**: `sqlalchemy_env` — the fixture is not appended if the string `sqlalchemy_env` already appears in `conftest.py`.

### Header (written once)

```python
"""Test fixtures for the generated project."""

from __future__ import annotations

import pytest
```

The header is only written when `conftest.py` does not yet contain `import pytest`. This prevents duplicate headers when multiple adapter types (e.g., `rest-consumer` + `sqlalchemy`) are generated for the same project.

### Coexistence example (rest-consumer + sqlalchemy)

```python
"""Test fixtures for the generated project."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def rest_consumer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REST_CONSUMER_BASE_URL", "https://example.com")


@pytest.fixture(autouse=True)
def sqlalchemy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
```

This file must parse as valid Python (`ast.parse` must succeed).

---

## `dm --name sqlalchemy` Cleanup

`scaffold dm --name sqlalchemy --confirm` removes:

1. `src/my_app/infrastructure/driven_adapters/sqlalchemy/` directory.
2. `src/tests/infrastructure/driven_adapters/sqlalchemy/` directory.
3. `sqlalchemy_env` fixture block from `src/tests/conftest.py`.
4. If `conftest.py` has no remaining fixtures after removal, the header import block is removed and the file is deleted if empty.
5. `test_container_resolves_sqlalchemy` test from `test_wiring.py` (if present).

Fixtures belonging to other adapter types (e.g., `rest_consumer_env`) are **not** affected.

---

## `--gateway` Additions

When `--gateway book_repository` is specified:

| File | Change |
|------|--------|
| `sqlalchemy_repository.py` | `@wireup.injectable(as_type=BookRepository)` decorator; class inherits from `BookRepository` |
| `test_wiring.py` | `test_container_resolves_sqlalchemy` appended (via `append_wiring_test`) |
| `wiring.py` | `MISSING_ADAPTERS` updated via `sync_wiring_marker` to remove `book_repository` |
