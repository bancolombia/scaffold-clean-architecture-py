# Post-migration checklist

`scaffold up` does not run these; run all of them after resolving pending items.

1. `uv run ruff check --fix --select I . && uv run ruff format .` — once: 0.5.0 never formatted generated files.
2. `uv sync`
3. `uv run ruff check .`
4. `uv run ruff format --check .`
5. `uv run mypy --strict src/`
6. `uv run pytest` (includes `src/tests/application/config/test_wiring.py`, which builds the whole graph)
7. `scaffold vs`
8. `scaffold up --dry-run --report json` → `pending` is `[]` and every action has `"skipped": true`.
9. `git diff --stat` reviewed with the user before committing.
