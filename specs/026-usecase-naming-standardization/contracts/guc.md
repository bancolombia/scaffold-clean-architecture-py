# CLI Contract changes: `scaffold guc` / `scaffold generate-use-case`

Flags, aliases, the no-argument help, name validation, and project-root errors stay the same. Only the generated names and two error cases change.

## Outputs

| `--name` | Created files | Class |
|---|---|---|
| `create_order` | `src/<pkg>/domain/usecase/create_order_usecase.py`, `src/tests/domain/usecase/test_create_order_usecase.py` | `CreateOrderUseCase` |
| `create_order_usecase` | same as above | `CreateOrderUseCase` |
| `create_order_use_case` | same as above | `CreateOrderUseCase` |
| `create_order_usecase_usecase` | same as above | `CreateOrderUseCase` |
| `usecase_registry` | `usecase_registry_usecase.py`, `test_usecase_registry_usecase.py` | `UsecaseRegistryUseCase` |

The generated test imports `from <pkg>.domain.usecase.<base>_usecase import <Base>UseCase`.

## Outcomes

| Situation | Exit | Output | Effect |
|---|---|---|---|
| Success | 0 | `✓ Use case <Base>UseCase created. Created 2 file(s).` | 2 files written |
| `--dry-run` | 0 | Tree titled `<base>_usecase (dry run)` listing the 2 paths | nothing written |
| `<base>_usecase.py` already exists (any spelling) | 1 | `Error: File 'src/<pkg>/domain/usecase/<base>_usecase.py' already exists.` plus the existing hint | nothing written |
| `src/tests/domain/usecase/test_<base>_usecase.py` already exists | 1 | `Error: File 'src/tests/domain/usecase/test_<base>_usecase.py' already exists.` plus the same hint | nothing written |
| Legacy `<base>.py` exists | 0 | normal success | `<base>_usecase.py` created, legacy file untouched, no warning |
| Name is only the suffix (`usecase`, `use_case`, `usecase_usecase`) | 1 | `Error: Use case name '<name>' is only the 'usecase' suffix.` / `Hint: Use a descriptive name such as 'create_order'.` | nothing written |

## Help text

Epilog example becomes:

```text
Example:

  * scaffold guc --name create_order   (creates domain/usecase/create_order_usecase.py)

  * scaffold generate-use-case --name create_order
```
