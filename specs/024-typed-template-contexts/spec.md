# Feature: Typed Template Contexts (024)

## Context

During the 022 refactor, template rendering calls were identified that pass plain `dict[str, Any]` context objects rather than typed Pydantic models or dataclasses. This makes it hard to know which keys a template expects, causes silent breakage when a key is renamed, and prevents static analysis.

Research notes from 022 (R-05 and R-16) identified two improvements:
- **R-05**: A typed `build(builder, options)` signature for factories that need per-type options beyond what `ModuleBuilder` carries (e.g., `--with-resources`, `--with-prompts` for MCP).
- **R-16**: A shared `render_into(builder, template, context_model)` helper that replaces the duplicated `tpl()` / `builder.render()` pattern inside each factory.

## Debt measured in 022

From `specs/022-solid-code-cleanup/plan.md` — Complexity Tracking:

- Multiple `dict[str, object]` / `dict[str, Any]` template context objects assembled inline inside `build()` methods.
- Per-factory `tpl()` / `_tmpl()` helpers duplicated across driven adapters and entry points.

## Goal

Replace ad-hoc `dict` template contexts with typed dataclasses or Pydantic models; introduce a shared `render_into` helper; optionally type-check the `build(builder, options)` signature for factories that consume extra flags.

## Success Criteria

- No `dict[str, Any]` or `dict[str, object]` template context in `factory/**/*.py`.
- A shared `render_into` (or equivalent) eliminates per-factory `tpl()` helpers.
- `mypy --strict` passes after the change.
- All existing tests pass unmodified.

## Scope

All `.py` files under `src/scaffold_ca_python/factory/`.
