# Feature: Consistent Error Hints (023)

## Context

During the 022 refactor, a survey of error messages in `src/scaffold_ca_python/` found approximately 38 `console.print("[red]Error:...")` calls that do not include a `[dim]Hint:[/dim]` line telling the user what to do next. Users who hit these errors receive a diagnosis with no recovery path.

## Debt measured in 022

From `specs/022-solid-code-cleanup/plan.md` — Complexity Tracking:

- ~38 error messages without a `Hint:` clause identified across `commands/`, `factory/`, and `core/`.

## Goal

Add a `[dim]Hint:[/dim] <actionable advice>` line to every user-facing error message that does not already have one, so that every error tells the user both _what_ went wrong and _what to do about it_.

## Success Criteria

- `grep -rn '\[red\]Error:\[/red\]' src/ | grep -v Hint` returns 0 lines (no un-hinted errors).
- All existing tests pass unmodified.
- New tests assert hint text is present for each modified error path.

## Scope

All `.py` files under `src/scaffold_ca_python/commands/`, `src/scaffold_ca_python/factory/`, and `src/scaffold_ca_python/core/`.
