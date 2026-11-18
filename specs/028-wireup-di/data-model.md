# Data Model: Wireup DI for New Projects

**Feature**: 028-wireup-di

This document describes the key entities and state transitions introduced or modified by this feature.

---

## Entities

### ProjectContext

Extended with `scaffold_version` and `is_legacy`.

| Field | Type | Validation | Notes |
|-------|------|------------|-------|
| `name` | `str` | kebab-case or snake_case | existing |
| `python_package` | `str` (computed) | snake_case of name | existing |
| `python_package_script` | `str` (computed) | kebab-case of name | existing |
| `scaffold_version` | `str \| None` | semver string or dev version | **NEW** — `None` when key is absent (legacy project); set by `generate-project` (spec 029 may update it during migration) |
| `is_legacy` | `bool` (property) | `scaffold_version is None` | **NEW** — `True` for ≤ 0.5.0 projects that were never generated or migrated with 0.6.0+ |

**State transition**:
```
pyproject.toml [tool.scaffold-ca-python] missing scaffold_version key
  → load_project_context → ProjectContext(scaffold_version=None, is_legacy=True)   # legacy

pyproject.toml [tool.scaffold-ca-python] scaffold_version = "0.6.0"
  → load_project_context → ProjectContext(scaffold_version="0.6.0", is_legacy=False)  # new
```

**Detection note**: Legacy detection is by presence of the key, not version comparison — dev versions (`0.5.1.devN+g…`) would break a `< 0.6.0` check, and 0.5.0 projects never had the key at all.

---

### UseCase Factory File

Generated at `application/config/usecases/<snake_name>.py`. One file per use case.

| Attribute | Value |
|-----------|-------|
| Location | `<project_src>/application/config/usecases/<snake_name>.py` |
| Content | Single `@injectable`-decorated factory function returning `<ClassName>UseCase` |
| Constructor params | One per gateway listed in `--uses`; typed as the gateway ABC |
| Created by | `generate-use-case` |
| Deleted by | `delete-module` (together with the use-case class file) |
| Discovered by | wireup package scan of `application.config.usecases` |

**Template variables** (for `use_case_factory.py.jinja2`):
- `class_name`: PascalCase class name (e.g., `CreateOrder`)
- `module_name`: snake_case module name (e.g., `create_order_usecase`)
- `gateways`: list of `{name: str, type: str, import_path: str}`
- `project.python_package`: root package name

---

### Adapter Settings

A `BaseSettings` subclass generated in the adapter's own package.

| Attribute | Value |
|-----------|-------|
| Class name | `<AdapterName>Settings` |
| Base class | `BaseSettings` (pydantic-settings) |
| `env_prefix` | derived from adapter name (e.g., `REST_CONSUMER_`) |
| Required fields | connection params without defaults (e.g., `base_url: str`) |
| Optional fields | operational params with defaults (e.g., `timeout: int = 5`) |
| Injected as | `<AdapterName>Settings` type, discovered by wireup |

---

### Resource Config File (D6 convention)

Optional file in adapter package for adapters with lifecycle resources.

| Attribute | Value |
|-----------|-------|
| File name | `<adapter_name>_config.py` |
| Location | same package as the adapter |
| Content | Async factory function with `yield`; opens resource, yields it, closes it |
| Decorator | `@injectable` |
| Resource type | any third-party class (e.g., `httpx.AsyncClient`, `asyncpg.Pool`) |
| Lifecycle | opened on first container warm-up; closed when container closes |

---

### Wiring.py structure (generated)

```python
# application/config/wiring.py
from __future__ import annotations
import wireup
from wireup.ioc.container.async_container import AsyncContainer
from <package>.infrastructure import driven_adapters, helpers
from <package>.application.config import usecases

INJECTABLES = [driven_adapters, helpers, usecases]

def create_container(settings: Settings | None = None) -> AsyncContainer:
    """Single async container; adapters discover by package scan."""
    return wireup.create_async_container(injectables=INJECTABLES)
```

---

## Legacy project guard (FR-020)

```
State: Legacy project (scaffold_version key absent)
  └─ any project-modifying generate-* command → EXIT 1
       message points to docs/spec-029-migrate-di/
```

Migration state transitions: [docs/spec-029-migrate-di/data-model.md](../../docs/spec-029-migrate-di/data-model.md).
