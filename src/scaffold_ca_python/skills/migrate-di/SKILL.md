# migrate-di

Migrate a legacy dependency-injector project to wireup using `scaffold up`, then finish pending items by hand.

## Stop conditions

- Request user approval before running `scaffold up` without `--dry-run`.
- Request approval before any `git commit`.
- If a pending `kind` has no recipe, stop and ask the user.

## Flow

1. Ensure tests pass on the legacy tree.
2. Run `scaffold up --dry-run` and review diffs plus pending JSON.
3. Run `scaffold up` after approval.
4. Complete pending items using `references/recipes.md`.
5. Run verification from `references/checklist.md` (ruff, mypy, pytest — not run by `scaffold up`).
