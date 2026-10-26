# Data Model: Use Case Naming Standardization

No new runtime models. The feature derives three names from the user's `--name` value and reuses the existing `ModuleContext`.

## Derived names

| Name | Rule | Example (`--name create_order_usecase`) |
|---|---|---|
| Raw name | `--name` as typed. Validated by `validate_module_name` (snake_case only). | `create_order_usecase` |
| Base name | `strip_usecase_suffix(raw)` (research R2). Must be non-empty. | `create_order` |
| Module name | `<base>_usecase` | `create_order_usecase` |
| Class name | `to_pascal_case(base) + "UseCase"` | `CreateOrderUseCase` |

## ModuleContext usage

`ModuleContext(name=<base>, layer=Layer.DOMAIN_USECASE, project=...)`. It is unchanged, only the value passed as `name` differs.

| Field | Value | Used by |
|---|---|---|
| `name` | base name | factory path |
| `class_name` | `<Base>` | both templates (`{{ class_name }}UseCase`), success message |
| `module_name` | `<base>` | factory path (`<base>_usecase.py`), test import (`{{ module_name }}_usecase`), test function name |

## Generated files

| File | Path |
|---|---|
| Use case module | `src/<pkg>/domain/usecase/<base>_usecase.py` |
| Test stub | `src/tests/domain/usecase/test_<base>_usecase.py` |

## Validation rules

1. The raw name must match snake_case (existing rule, existing message).
2. The base name must be non-empty. Otherwise exit 1 with a hint (FR-008).
3. `src/<pkg>/domain/usecase/<base>_usecase.py` must not exist. Otherwise exit 1 with a hint (FR-009). Legacy `<base>.py` is ignored (FR-009a).
4. `src/tests/domain/usecase/test_<base>_usecase.py` must not exist. Otherwise exit 1 with a hint (FR-009b).
