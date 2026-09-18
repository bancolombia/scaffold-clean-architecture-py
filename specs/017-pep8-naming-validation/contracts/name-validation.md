# Contract: `--name` Argument Validation

**Type**: CLI input validation contract  
**Applies to**: Scaffold commands accepting `--name`

The naming policy is split by command family (`gep` takes `--type`, not `--name`):

| Command family | Commands | Accepted input |
|----------------|----------|----------------|
| Project | `ca` | `kebab-case` **or** `snake_case` |
| Module/class | `gm`, `guc`, `gh`, `gda --type generic`, `dm` | `snake_case` only |

Rationale: `ca` names a project directory and PyPI distribution, where `kebab-case` is
idiomatic. `gm`/`guc`/`gh`/`gda`/`dm` generate a Python module (`snake_case` file) plus a
`PascalCase` class; accepting `kebab-case` there is ambiguous noise, so only `snake_case`
(the PEP8 module form) is allowed.

---

## Accepted Values — `ca` (kebab-case or snake_case)

A valid `ca --name` value MUST match:

```
^[a-z][a-z0-9]*([_-][a-z0-9]+)*$
```

| Format | Example | Accepted |
|--------|---------|----------|
| Single lowercase word | `order` | ✅ |
| `snake_case` | `my_project` | ✅ |
| `kebab-case` | `my-project` | ✅ |
| Alphanumeric (no separator) | `project2025` | ✅ |
| `PascalCase` | `MyProject` | ❌ |
| `camelCase` | `myProject` | ❌ |
| Consecutive separators | `my--project` | ❌ |
| Leading/trailing separator | `-my`, `my_` | ❌ |
| Starts with digit | `1project` | ❌ |
| Special characters | `my@project` | ❌ |
| Empty string | `` | ❌ |

## Accepted Values — module/class commands (snake_case only)

A valid `--name` value for `gm`/`guc`/`gh`/`gda --type generic`/`dm` MUST match:

```
^[a-z][a-z0-9]*(_[a-z0-9]+)*$
```

| Format | Example | Accepted |
|--------|---------|----------|
| Single lowercase word | `order` | ✅ |
| `snake_case` | `create_order` | ✅ |
| `kebab-case` | `create-order` | ❌ |
| `PascalCase` | `CreateOrder` | ❌ |
| `camelCase` | `createOrder` | ❌ |

The error message for these commands MUST mention `snake_case` (e.g.,
`Invalid name 'create-order'. Use snake_case (e.g., 'create_order').`).

---

## Error Response (invalid name)

When validation fails, the tool MUST exit with code **1** and print to stdout:

- For `ca`: a message containing both `kebab-case` and `snake_case`.
  ```
  Error: Invalid name 'MyProject'. Use kebab-case (e.g., 'my-project') or snake_case (e.g., 'my_project').
  ```
- For module/class commands: a message containing `snake_case`.
  ```
  Error: Invalid name 'create-order'. Use snake_case (e.g., 'create_order').
  ```

---

## Internal Normalisation

For `ca`, `kebab-case` input is silently normalised to `snake_case` for the Python package
(`to_snake_case`) and kept as `kebab-case` for the distribution script (`to_kebab_case`); no
warning is printed. Module/class commands only accept `snake_case`, so their input needs no
kebab normalisation; the `PascalCase` class name is still derived via `to_pascal_case`.

The normalisation helpers themselves remain kebab-tolerant (they are also fed `ProjectContext`/
`ModuleContext` values built directly in tests):

| Input | Module name | Class name |
|-------|-------------|------------|
| `create_order` | `create_order` | `CreateOrder` |
| `order` | `order` | `Order` |
| `my_order_service` | `my_order_service` | `MyOrderService` |

---

## Invariants

1. **Generated `.py` file names**: always `snake_case` — `[a-z][a-z0-9_]*\.py`
2. **Generated `class` names**: always `PascalCase` — `[A-Z][a-zA-Z0-9]*`
3. **Validation applies regardless of `--dry-run`**
4. **Validation policy is split by command family** — `ca` accepts `kebab-case`/`snake_case`;
   `gm`/`guc`/`gh`/`gda --type generic`/`dm` accept `snake_case` only; `gep` takes `--type`,
   not `--name`. No command bypasses its family's rule.
