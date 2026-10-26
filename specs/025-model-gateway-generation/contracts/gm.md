# CLI Contract: `scaffold gm` / `scaffold generate-model`

## Synopsis

```text
scaffold gm --name <snake_name> [--dry-run]
scaffold generate-model --name <snake_name> [--dry-run]
```

## Outcomes

| Situation | Exit | Output | Disk |
|---|---|---|---|
| No `--name` | 0 | help text | unchanged |
| Invalid name (`Paper`, `my-paper`, `1paper`) | 1 | existing snake_case validation error | unchanged |
| Outside a project root | 1 | `No scaffold-ca-python project found. Run 'scaffold ca' first.` | unchanged |
| `domain/model/<name>/` exists | 1 | `Error: Directory 'src/<pkg>/domain/model/<name>/' already exists.` + hint | unchanged |
| `domain/model/<name>.py` exists (legacy) | 1 | `Error: File 'src/<pkg>/domain/model/<name>.py' already exists.` + hint | unchanged |
| `src/tests/domain/model/<name>/` exists | 1 | `Error: Directory 'src/tests/domain/model/<name>/' already exists.` + hint | unchanged |
| `--dry-run`, no conflict | 0 | tree titled `<name> (dry run)` listing the 6 files from [data-model.md](../data-model.md) | unchanged |
| Success | 0 | `✓ Model <ClassName> created. Created 6 file(s).` | 6 files created |

Conflict checks run in the order above, before any file is written.

## Generated gateway (shape)

```python
"""<ClassName> gateway."""

from abc import ABC


class <ClassName>Repository(ABC):
    """Repository contract for <ClassName>. Add the operations your domain needs."""
```

## Generated gateway test (shape)

```python
from abc import ABC

from <pkg>.domain.model.<name>.gateways.<name>_repository import <ClassName>Repository


def test_<name>_repository_is_abstract_contract() -> None:
    assert issubclass(<ClassName>Repository, ABC)
```
