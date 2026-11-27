# Quickstart: validating the 022 refactor

End-to-end validation guide. Design details are in [data-model.md](data-model.md) and [contracts/](contracts/).

## Prerequisites

```bash
export SSL_CERT_FILE=/etc/ssl/cert.pem   # only if uv fails with a TLS error
uv sync
git switch feature/022-solid-code-cleanup
REPO=/path/to/scaffold-clean-architecture-py
```

## 1. Reference tree (before the refactor)

Run once from `main`, before starting:

```bash
gen_tree() {   # $1 = output dir, $2 = sha file
  mkdir -p "$1" && cd "$1"
  uv run --project "$REPO" scaffold-ca-python ca --name demo-app
  cd demo-app
  for t in "gm --name order" "guc --name create_order" "gh --name clock" \
           "gda --type rest-consumer" "gda --type generic --name cache" \
           "gep --type mcp --with-resources" "gep --type mcp --add-tool --name ping --returns str" \
           "gpipe --provider github"; do
    uv run --project "$REPO" scaffold-ca-python $t
  done
  sed -i '' '/^created_at = /d' pyproject.toml          # timestamp differs on every run
  find . -type f -print0 | sort -z | xargs -0 shasum > "$2"
}
gen_tree /tmp/ref022 /tmp/ref022.sha
```

Repeat for restapi in another directory, because restapi is incompatible with mcp. Use `ca --name demo-api`, then `gep --type restapi` and `gda --type secrets`, and save the hashes to `/tmp/ref022-restapi.sha`.

After the refactor, run the same thing in `/tmp/new022` and `/tmp/new022-restapi`, then compare:

```bash
diff /tmp/ref022.sha /tmp/new022.sha
diff /tmp/ref022-restapi.sha /tmp/new022-restapi.sha
```

**Expected**: no differences. This covers User Story 1 and SC-001.

## 2. Suite and guardrails

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

**Expected**:
- Everything is green, with coverage ≥80% (baseline: 96.50%).
- The 739 existing tests pass, plus the new ones. Only the tests listed in research R-08 and those of C-1, C-2 and C-3 are adapted.

This covers SC-001, SC-002 and SC-007.

## 3. Measurable criteria

```bash
# SC-003: zero Spec Kit IDs in src/
grep -rnE '\b(T0[0-9]{2}|FR-[0-9]{3}|US-?[0-9]|R-[0-9]{2})\b|Phase [0-9]' src/ | grep '\.py:' | wc -l   # → 0

# SC-004: single definitions
grep -rn "def load_project_context\|def _load_project_context" src/ | wc -l             # → 1
grep -rn "No scaffold-ca-python project found" src/ | wc -l                            # → 1

# SC-005: no type literals in commands/ (except add_mcp_tool.py)
grep -nE '"(restapi|agent|generic|rest-consumer|secrets|github|azure)"' src/scaffold_ca_python/commands/*.py   # → empty

# No temporary C901 ignores left
grep -n "C901" pyproject.toml                                                           # → empty

# FR-004: only the two new templates were added; nothing existing was modified
git diff --stat main -- src/scaffold_ca_python/templates
```

## 4. Allowed behavior changes

- **C-1 (FR-010)**: run `uv run pytest tests/core/test_project_context.py`. It uses a project whose `[project].name` differs from `[tool.scaffold-ca-python].name`; `gep` and `gm` must resolve the same package.
- **C-2 (FR-016)**: run `scaffold-ca-python gpipe --provider github` twice. The second error does not mention `--force`.
- **C-3 (FR-021)**: `scaffold-ca-python gep --type restapi --dry-run` shows `Would update [project.scripts]: <pkg> = "<pkg>.server:start_server"`.

## 5. Extensibility

```bash
uv run pytest tests/factory/test_extensibility.py -v
```

**Expected**: the fake factory registered in `ENTRY_POINT_FACTORIES` generates its files, validates flags and shows its notes, and `commands/` was not modified.
