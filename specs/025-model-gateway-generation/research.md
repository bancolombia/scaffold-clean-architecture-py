# Research: Model Gateway Generation

## R1. Shape of the generated gateway

- **Decision**: An empty class `<ClassName>Repository(ABC)` with only a docstring. It imports only `from abc import ABC`.
- **Rationale**: The model name is just a CLI parameter, and the CLI cannot know the project's domain (clarification 2026-10-26). An empty contract avoids guessing operations. Importing the model without using it would fail the generated project's ruff F401 rule.
- **Alternatives considered**:
  - One or two abstract async methods (`save`, `find_by_id`). Rejected by the user because they assume domain knowledge.
  - `typing.Protocol`. Rejected because the user asked for `abc.ABC`, and driven adapters in this project subclass their ports.

## R2. What the gateway test can verify

- **Decision**: The generated test asserts `issubclass(<ClassName>Repository, ABC)`.
- **Rationale**: An `ABC` subclass without abstract methods can still be instantiated, so a "raises `TypeError`" test would fail out of the box. The subclass check is true, stays meaningful once methods are added, and keeps the generated suite green.
- **Alternatives considered**: `inspect.isabstract(...)`. It returns `False` while there are no abstract methods, so it would fail.

## R3. Package markers

- **Decision**: Generate `__init__.py` in `domain/model/<name>/` and `domain/model/<name>/gateways/`. Each one contains a single-line docstring, rendered from its own template (`__init__.py.jinja2`, `gateways_init.py.jinja2`). Test folders get no `__init__.py`.
- **Rationale**: The generated project's `domain/model/` already has an `__init__.py` (`generate_project.py` `_LAYER_DIRS`), so new source sub-packages follow the same pattern. Generated pytest runs with `--import-mode=importlib`, so tests with duplicate basenames in different folders work without package markers. The helper generator already relies on this.
- **Alternatives considered**: Implicit namespace packages, with no `__init__.py`. Rejected because they are inconsistent with the rest of the generated layout and some tools handle them poorly.

## R4. Conflict detection

- **Decision**: Before building, `generate_model.py` calls the existing `ensure_absent` helper for (1) `src/<pkg>/domain/model/<name>/`, (2) `src/<pkg>/domain/model/<name>.py`, and (3) `src/tests/domain/model/<name>/`. Each failure exits with code 1 and a hint.
- **Rationale**: If a test file already exists, `FileWriter._preflight` raises an unhandled `FileExistsError`, and by then it has already created parent folders. Checking up front keeps the command all-or-nothing and gives a clean message. It reuses an existing helper.
- **Alternatives considered**: Catching `FileExistsError` in the command. Rejected because empty folders could still be left behind.

## R5. Lookup and deletion of the new layout

- **Decision**: `find_module_targets` adds a `(domain/model/<snake>/, tests/domain/model/<snake>/)` directory candidate, checked before the legacy flat-file candidate. `DeleteModuleFactory.build` iterates `find_module_targets(...)` instead of keeping its own duplicate candidate list.
- **Rationale**: Today the same path list exists in both modules. Adding the new layout in two places would invite drift. `DeleteModuleFactory._delete_path` already removes directories with `shutil.rmtree`.
- **Alternatives considered**: Editing both lists. Rejected because it duplicates logic.

## R6. Structure validation

- **Decision**: No change to `structure_validator.py`.
- **Rationale**: `_layer_from_path_parts` matches on the `("domain", "model")` prefix, so `domain/model/<name>/gateways/*.py` already maps to `Layer.DOMAIN_MODEL`.
