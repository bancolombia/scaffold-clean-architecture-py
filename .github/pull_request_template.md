Before submitting a pull request, please read [CONTRIBUTING.md](https://github.com/bancolombia/scaffold-clean-architecture-py/blob/main/CONTRIBUTING.md).

## Description
<!-- What does this change and why? Link the issue it resolves (e.g. "Closes #123"). -->

## Category
- [ ] Feature
- [ ] Fix
- [ ] Refactor
- [ ] CI / Docs / Chore

## Spec
<!-- For features: link the spec directory, e.g. specs/030-sqlalchemy-adapter/. Write "N/A" for fixes and docs. -->

## Checklist
- [ ] The PR title follows [Conventional Commits](https://www.conventionalcommits.org/) and makes sense in the changelog (e.g. `feat(gda): add sqlalchemy driven adapter`).
- [ ] Tests were written first and cover the change; `uv run pytest` passes with ≥ 80 % coverage.
- [ ] `uv run ruff check src tests`, `uv run ruff format --check src tests` and `uv run mypy src` pass.
- [ ] If templates, factories or generated output changed: `uv run pytest -m e2e --no-cov` passes.
- [ ] New or changed templates have rendering tests in `tests/templates/`, and `tests/factory/fixtures/dry_run_baseline.json` is up to date.
- [ ] A new driven-adapter or entry-point type is registered, documented in the README and covered by a scenario in `tests/e2e/test_generated_project_quality.py`.
- [ ] Changes to files that existing generated projects already contain include an upgrade action and migration docs (see [CONTRIBUTING.md](https://github.com/bancolombia/scaffold-clean-architecture-py/blob/main/CONTRIBUTING.md#change-files-that-already-exist-in-generated-projects)).
- [ ] The README and `--help` texts reflect any user-visible change.
