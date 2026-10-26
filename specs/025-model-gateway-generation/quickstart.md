# Quickstart: validate model gateway generation

## Prerequisites

- Branch `feature/model-gateway-generation` checked out
- `uv sync` done in the repository root

## 1. Generate a project and a model

```bash
cd "$(mktemp -d)"
uv run --project /path/to/scaffold-clean-architecture-py scaffold ca --name my-app
cd my-app
uv run --project /path/to/scaffold-clean-architecture-py scaffold gm --name research_paper --dry-run
uv run --project /path/to/scaffold-clean-architecture-py scaffold gm --name research_paper
```

**Expected**: The dry run lists the 6 files from [data-model.md](data-model.md) and creates nothing. The real run prints `Created 6 file(s).` and creates the tree below.

```text
src/my_app/domain/model/research_paper/
├── __init__.py
├── research_paper.py
└── gateways/
    ├── __init__.py
    └── research_paper_repository.py
src/tests/domain/model/research_paper/
├── test_research_paper.py
└── gateways/test_research_paper_repository.py
```

## 2. Generated project checks pass

```bash
uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest
uv run --project /path/to/scaffold-clean-architecture-py scaffold vs
```

**Expected**: All commands exit 0, and `vs` reports no violations.

## 3. Conflicts

```bash
uv run --project /path/to/scaffold-clean-architecture-py scaffold gm --name research_paper; echo $?
```

**Expected**: exit code `1`, a "Directory ... already exists" error with a hint, and no file changes. For the legacy and tests-folder conflicts, see [contracts/gm.md](contracts/gm.md).

## 4. Delete

```bash
uv run --project /path/to/scaffold-clean-architecture-py scaffold dm --name research_paper --confirm
```

**Expected**: `src/my_app/domain/model/research_paper/` and `src/tests/domain/model/research_paper/` no longer exist.

## 5. CLI suite

```bash
cd /path/to/scaffold-clean-architecture-py
uv run ruff check && uv run ruff format --check && uv run mypy src && uv run pytest
```

**Expected**: All checks pass with coverage at or above 80%.
