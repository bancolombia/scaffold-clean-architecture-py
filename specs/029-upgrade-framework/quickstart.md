# Quickstart: Migrate a 0.5.0 project with `scaffold up`

**Prerequisites**: scaffold-ca-python ≥ 1.0.1, `uv`, git, Python 3.13+.

---

## Scenario 1 — Preview migration

```bash
cd my_legacy_service
git status   # must be clean for real apply
scaffold up --dry-run
```

Expect unified diffs for pyproject, new factory files, and entry-point param changes; pending list for `Resource` providers or edited `application/app.py`.

---

## Scenario 2 — Apply automated migration

```bash
scaffold up
```

Expect: actions run, then `uv lock --upgrade`, then `uv sync`. Review stderr report; use `scaffold up --report json` to feed an agent.

---

## Scenario 3 — Install agent skill

```bash
scaffold install-skill migrate-di --target all
```

Follow `SKILL.md` and `references/checklist.md` for ruff, mypy, and pytest. Do not expect `scaffold up` to run those tools.

---

## Scenario 4 — JSON report for automation

```bash
scaffold up --report json > report.json
```

Only JSON on stdout; read human messages from stderr.

---

## Scenario 5 — Dependency-only update

```bash
scaffold up --skip-upgrades
```

Same as today: lock + sync only.

---

## Known limitation

Multi-action dry-run does not chain in-memory state between actions; run a non-dry-run `up` after reviewing dry-run output if you need a second dry-run pass.