# Quickstart: Migrate a 0.5.0 project with `scaffold up`

**Prerequisites**: scaffold-ca-python ≥ 1.0.1, `uv`, git, Python 3.13+.

---

## Scenario 1 — Preview migration

```bash
cd my_legacy_service
git status   # must be clean for real apply
scaffold up --dry-run
```

Expect unified diffs (project-relative paths) for pyproject, new factory files, deleted containers and entry-point parameter changes; the pending list names `Resource` providers, edited composition roots, etc., each with `file:line` and a guide anchor.

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

Follow `SKILL.md` and `references/checklist.md` for ruff, mypy, and pytest. Do not expect `scaffold up` to run those tools. Run `uv run ruff format .` once: 0.5.0 never formatted its generated files, and `up` only formats the files it writes.

---

## Scenario 4 — JSON report for automation

```bash
scaffold up --report json > report.json
```

Only JSON on stdout; human messages, `uv` output and dry-run diffs go to stderr.

Re-run it after resolving items: the action is reported `"skipped": true` and `pending` is empty once nothing legacy remains.

---

## Scenario 5 — Dependency-only update

```bash
scaffold up --skip-upgrades
```

Same as today: lock + sync only.

---

## Scenario 6 — Project created before the scaffolder

```bash
cd my_older_service              # same layout, no [tool.scaffold-ca-python]
scaffold up --dry-run            # exit 1: prints the section to add
# add the printed [tool.scaffold-ca-python] block (no scaffold_version)
scaffold up --dry-run --report json
scaffold install-skill migrate-di   # agent follows references/pre-scaffold.md
```

Expect use cases in `domain/use_cases/` and gateways in `gateway/` to be recognized, and a larger pending list (configuration passed by value, resources, custom composition roots, container tests).

---

## Known limitation

Multi-action dry-run does not chain in-memory state between actions; run a non-dry-run `up` after reviewing dry-run output if you need a second dry-run pass.