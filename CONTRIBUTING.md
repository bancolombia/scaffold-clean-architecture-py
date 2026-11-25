# Contributing to scaffold-ca-python

Thank you for your interest in improving scaffold-ca-python. This guide explains how to set up the project, how changes are designed and reviewed, and what a pull request needs before it can be merged.

By participating you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Table of contents

- [Ways to contribute](#ways-to-contribute)
- [Development setup](#development-setup)
- [Repository layout](#repository-layout)
- [Development workflow](#development-workflow)
- [Spec-driven development](#spec-driven-development)
- [Coding standards](#coding-standards)
- [Testing](#testing)
- [Common contribution recipes](#common-contribution-recipes)
- [Commit messages](#commit-messages)
- [Pull requests](#pull-requests)
- [Releases](#releases)

## Ways to contribute

- **Report a bug** — open an [issue](https://github.com/bancolombia/scaffold-clean-architecture-py/issues) with the scaffold-ca-python version (`pip show scaffold-ca-python`), the exact command you ran, the output and what you expected.
- **Propose a feature** — open an issue describing the problem first. New commands, adapter types or entry-point types change the public CLI, so agree on the design before writing code.
- **Improve the documentation** — fixes to the README, the migration guides or `--help` texts are always welcome.
- **Send a pull request** — for an open issue, or for small, self-evident fixes.

Security vulnerabilities must **not** be reported in public issues; follow [SECURITY.md](SECURITY.md).

## Development setup

**Prerequisites:** Python 3.13+, [uv](https://docs.astral.sh/uv/) and git.

1. Fork [bancolombia/scaffold-clean-architecture-py](https://github.com/bancolombia/scaffold-clean-architecture-py) and clone your fork:

   ```bash
   git clone https://github.com/<your-user>/scaffold-clean-architecture-py.git
   cd scaffold-clean-architecture-py
   ```

2. Install the dependencies (the `dev` group is included by default):

   ```bash
   uv sync
   ```

3. Install the git hooks (ruff check, ruff format, mypy and file hygiene run on every commit):

   ```bash
   uv run prek install
   ```

4. Check that everything is green:

   ```bash
   uv run pytest
   ```

5. Try the CLI from your checkout:

   ```bash
   uv run scaffold --help
   # from another directory, e.g. inside a generated project:
   uv run --project /path/to/scaffold-clean-architecture-py scaffold gm --name order
   ```

> **Corporate networks:** if `uv` fails with TLS or certificate errors (custom CAs, proxies), export `UV_SYSTEM_CERTS=1` so it uses the system certificate store. This is a local setting; do not add it to CI or project files.

## Repository layout

```text
src/scaffold_ca_python/
├── cli.py                 # Typer app; registers every command
├── commands/              # one module per CLI command (argument parsing, validation, output)
├── factory/               # what each command generates
│   ├── driven_adapters/   # one factory per `gda --type` (registry: DRIVEN_ADAPTER_FACTORIES)
│   ├── entry_points/      # one factory per `gep --type` (registry: ENTRY_POINT_FACTORIES)
│   ├── simple/            # model, use case, helper and delete-module factories
│   ├── pipelines/         # CI/CD providers
│   ├── upgrades/          # `scaffold up` actions (registry: UPGRADE_ACTIONS)
│   └── dependencies.py    # pinned dependencies injected into generated projects
├── core/                  # ModuleBuilder, file writer, renderer, validators
├── models/                # Pydantic models for template contexts and file operations
├── skills/                # agent skills shipped with `scaffold install-skill`
└── templates/             # Jinja2 templates, one directory per generator group
tests/                     # mirrors src/; tests/e2e/ generates real projects
specs/                     # one directory per feature (spec, plan, tasks)
.specify/memory/constitution.md   # project principles — the source of truth for reviews
```

## Development workflow

1. **Sync with `main`** and create a branch named `feature/<short-kebab-name>` (e.g. `feature/sqlalchemy-adapter`). Numbered branches such as `030-sqlalchemy-adapter` are also accepted.
2. **Design** the change. Features go through [spec-driven development](#spec-driven-development); bug fixes and docs can skip it.
3. **Write a failing test first**, then the minimum code to make it pass, then refactor under green.
4. **Run the local checks** before pushing:

   ```bash
   uv run ruff check src tests
   uv run ruff format --check src tests
   uv run mypy src
   uv run pytest
   uv run pytest -m e2e --no-cov   # when you change templates, factories or generated output
   ```

5. **Open a pull request** against `main` and fill in the template.

## Spec-driven development

Features are designed with [Spec Kit](https://github.com/github/spec-kit) before they are implemented. Each feature lives in `specs/<NNN>-<name>/`, and every artifact there is written in **English**.

| Step | Command | Output |
|---|---|---|
| 1. Specify | `/speckit-specify <feature description>` | `spec.md` — what and why, user stories, requirements |
| 2. Clarify | `/speckit-clarify` | Ambiguities resolved and recorded in `spec.md` |
| 3. Plan | `/speckit-plan` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| 4. Tasks | `/speckit-tasks` | `tasks.md` — ordered, test-first task list |
| 5. Analyze | `/speckit-analyze` | Consistency report; fix every CRITICAL and HIGH finding |
| 6. Implement | `/speckit-implement` | Code and tests, tasks checked off as they pass |

The plan must include a **Constitution Check** against [`.specify/memory/constitution.md`](.specify/memory/constitution.md). A violation can only remain if it already existed on `main` and is recorded as pre-existing debt with a follow-up feature, as the constitution's governance section describes.

## Coding standards

These rules come from the constitution and are enforced by tools, so CI fails when they are broken.

**Python**
- Full type hints on public interfaces; `mypy --strict` must pass.
- `ruff` is the only linter and formatter (line length 120).
- Functions take at most **5 positional arguments**; further parameters are keyword-only (`PLR0917`). Typer command options are keyword-only after `ctx`.
- Cyclomatic complexity of at most **10** per function (`C90`).
- No unused arguments in `src/` (`ARG`). Methods that override a framework or base-class method use `@typing.override`.

**Comments**
- Comments explain *why* (a hidden constraint, a workaround, a non-obvious invariant), never *what*.
- No commented-out code (`ERA`), no `# ---` banner comments.
- No Spec Kit identifiers (`T012`, `FR-003`, `US1`…) in source, tests or templates; they belong in `specs/` and PR descriptions. `tests/test_source_hygiene.py` enforces this.

**Code generation**
- Every generated file comes from a Jinja2 template under `src/scaffold_ca_python/templates/`; no f-string code assembly.
- Generated code must pass `ruff`, `mypy --strict`, `pytest` and `scaffold vs` with no manual edits, and use async I/O.
- Dependencies injected into generated projects are declared in `factory/dependencies.py` with a compatible-release pin (`~=X.Y.Z`).
- Every command supports `--dry-run`, prints Rich output, and every error includes a hint telling the user what to do next.

## Testing

| Suite | Command | Runs |
|---|---|---|
| Unit (default) | `uv run pytest` | Everything except `e2e` and `benchmark`, with an **80 % coverage gate** |
| End-to-end | `uv run pytest -m e2e --no-cov` | Generates real projects, runs `uv sync`, ruff, mypy, pytest and `scaffold vs` on them (several minutes) |
| Benchmarks | `uv run pytest -m benchmark --no-cov` | Performance tests |

Guidelines:
- Keep the default suite fast. Tests that invoke `uv` for real belong in `tests/e2e/`, and every module there declares `pytestmark = pytest.mark.e2e` (enforced by `tests/test_source_hygiene.py`). Mock `subprocess.run` in unit tests.
- Every template group needs rendering tests in `tests/templates/` that assert key names, imports and async syntax.
- Follow pytest idioms (`PT`): one condition per `assert`, `pytest.raises` with `match=` or a specific exception, tuple `parametrize` names.
- When a command creates, removes or renames files, update `tests/factory/fixtures/dry_run_baseline.json`. `tests/factory/test_dry_run_parity.py` compares the dry-run output with it.

## Common contribution recipes

### Add a driven-adapter or entry-point type

1. Write the failing tests: factory tests in `tests/factory/`, command tests in `tests/commands/`, template tests in `tests/templates/`.
2. Add the templates under `templates/driven_adapter/<type>/` (or `templates/entry_point/<type>/`), including the test stub for the generated project.
3. Create the factory (`factory/driven_adapters/da_<type>.py` extending `DrivenAdapterFactory`, or an `EntryPointFactory`) and register it in `DRIVEN_ADAPTER_FACTORIES` or `ENTRY_POINT_FACTORIES`.
4. Declare any new runtime or test dependency in `factory/dependencies.py`.
5. Update `dry_run_baseline.json`, add an end-to-end scenario to `tests/e2e/test_generated_project_quality.py`, and document the type in the README.

### Change files that already exist in generated projects

Generated projects outlive the version that created them. If you change the structure or content of files that `scaffold ca` (or another command) has already written, add an **upgrade action** so existing projects can follow:

1. Create `factory/upgrades/actions/upgrade_<yyyy>_<mm>_<dd>_<description>.py` implementing `UpgradeAction`. It must be idempotent and report what it could not migrate.
2. Register it in `UPGRADE_ACTIONS` (`factory/upgrades/__init__.py`).
3. Add or update the guide in `docs/migration/` and its pending-item recipes.

## Commit messages

Commits follow [Conventional Commits](https://www.conventionalcommits.org/). [release-please](https://github.com/googleapis/release-please) reads them to compute the next version and write `CHANGELOG.md`, so the type matters:

| Type | Use for | Changelog |
|---|---|---|
| `feat` | New user-facing capability | Features (minor bump) |
| `fix` | Bug fix | Bug Fixes (patch bump) |
| `docs` | Documentation only | Documentation |
| `refactor` | Code change without behavior change | Refactoring |
| `perf` | Performance improvement | Performance |
| `test` | Tests only | hidden |
| `chore` | Tooling, dependencies, housekeeping | hidden |
| `style` | Formatting only | hidden |

Use a scope when it helps (`feat(gda): …`, `fix(cli): …`). Mark breaking changes with `!` (`feat(up)!: …`) or a `BREAKING CHANGE:` footer. Do not edit `CHANGELOG.md` by hand.

> The ruff-format hook may reformat files and abort the first commit attempt. Stage the reformatted files and commit again.

## Pull requests

Before requesting review, check that:

- [ ] The PR targets `main` and has a Conventional Commits title that makes sense in the changelog.
- [ ] Tests were written first and cover the change; `uv run pytest` passes with ≥ 80 % coverage.
- [ ] `ruff check`, `ruff format --check` and `mypy` pass.
- [ ] `uv run pytest -m e2e --no-cov` passes if templates, factories or generated output changed.
- [ ] New or changed templates have tests in `tests/templates/`; `dry_run_baseline.json` is up to date.
- [ ] Structural changes to generated projects include an upgrade action and migration docs.
- [ ] The README and `--help` texts reflect any user-visible change.
- [ ] Features link to their `specs/<NNN>-<name>/` directory.

CI runs three jobs on every pull request — **Lint & Type Check**, **Tests & Coverage** and **E2E (generated projects)** — and all of them must pass before a maintainer reviews and merges the change.

## Releases

Maintainers do not tag versions by hand:

1. Every merge to `main` updates the release pull request that release-please keeps open, with the next version and changelog.
2. Merging that pull request creates the git tag and the GitHub release.
3. The release triggers the publish workflow, which builds the package and uploads it to [PyPI](https://pypi.org/project/scaffold-ca-python/) through trusted publishing.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
