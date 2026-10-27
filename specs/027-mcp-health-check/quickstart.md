# Quickstart: Validating the MCP Health Check Route

**Feature**: `027-mcp-health-check`
**Audience**: Developer implementing or reviewing this feature

## Prerequisites

- Python ≥ 3.13 and [uv](https://docs.astral.sh/uv/)
- This repository on branch `feature/mcp-health-check`, with `uv sync` run once

## 1. CLI test suite

```bash
uv run pytest tests/templates/test_entry_point_templates.py tests/factory/entry_points/test_ep_mcp.py tests/factory/test_dry_run_parity.py
uv run pytest            # full suite, coverage gate ≥ 80%
uv run ruff check . && uv run mypy src
```

Expected: everything passes. The dry-run baseline includes `routes.py` and `test_routes.py` under `gep:mcp`.

## 2. Dry run in a throwaway project

```bash
cd /tmp
uv run --project /path/to/scaffold-clean-architecture-py scaffold ca --name demo-mcp
cd demo-mcp
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp --dry-run
```

Expected: the preview lists `mcp_server/routes.py` and `mcp_server/test_routes.py`, and nothing is written (see [contract §5](./contracts/generated-routes.md#5-cli-dry-run-contract)).

## 3. Generate and verify the generated project

```bash
uv run --project /path/to/scaffold-clean-architecture-py scaffold gep --type mcp
uv sync
uv run ruff check src
uv run pytest
```

Expected:

- `ruff` reports no issues for `routes.py` and `test_routes.py`.
- `test_routes.py` and `test_app.py` pass without edits.

## 4. Hit the endpoint

```bash
uv run demo-mcp &           # project script → server.main()
curl -i http://localhost:8000/api/v1/health
curl -i -X POST http://localhost:8000/api/v1/health
kill %1
```

Expected:

- `GET` returns `HTTP/1.1 200` with `{"status":"ok"}`.
- `POST` returns `HTTP/1.1 405`.

See [contract §1](./contracts/generated-routes.md#1-http-contract-generated-server).

## 5. Regression checks

- `scaffold gep --type mcp --with-resources --with-prompts` still generates `routes.py`, and the health check still answers.
- `scaffold gep --type mcp --add-tool --name foo --returns str --description "x"` leaves `routes.py` and the `bind_routes` line in `app.py` untouched.
