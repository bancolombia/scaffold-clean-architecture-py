# dependency-injector → wireup

Use `scaffold up` on projects generated with scaffold-ca-python 0.5.0 (no `scaffold_version` in `pyproject.toml`).

## Automated steps

- Swap `dependency-injector` for `wireup==2.13.0`.
- Write `application/config/wiring.py` and `application/config/usecases/`.
- Remove legacy `*_container.py` modules.
- Convert common `Provide[...]` patterns to `Injected[...]` in entry points.

## Manual follow-up

Pending JSON kinds are documented in `specs/029-upgrade-framework/contracts/pending-items.md`.

## Verification

Run ruff, mypy, and pytest on the target project (see skill `references/checklist.md`).
