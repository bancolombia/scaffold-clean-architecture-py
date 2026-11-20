# Post-migration checklist

After `scaffold up` and pending resolution:

1. `uv sync`
2. `uv run ruff check .`
3. `uv run ruff format --check .`
4. `uv run mypy --strict src/`
5. `uv run pytest`
