# scaffold-ca-python

[![PyPI version](https://img.shields.io/pypi/v/scaffold-ca-python.svg)](https://pypi.org/project/scaffold-ca-python/)
[![Python](https://img.shields.io/pypi/pyversions/scaffold-ca-python.svg)](https://pypi.org/project/scaffold-ca-python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## What is this?

`scaffold-ca-python` is a CLI tool that scaffolds production-ready Python projects that follow Clean Architecture. It helps teams start faster by generating the project structure, modules, adapters, entry points, helpers, and pipeline files needed to keep architectural boundaries explicit. It is designed for developers who want repeatable code generation instead of hand-creating the same project pieces over and over.

## Installation

Python 3.13 or newer is required.

Install with `pip`:

```bash
pip install scaffold-ca-python
```

Install with `uv`:

```bash
uv add scaffold-ca-python
```

You could also use `uvx`:

```bash
uvx scaffold-ca-python [command]
```

Use `--help` to see all available command.

## Quick Start

1. Create a new Clean Architecture project.

```bash
scaffold ca --name my-app
```

2. Move into the generated project directory.

```bash
cd my-app
```

3. Generate a domain model.

```bash
scaffold gm --name order
```

4. Validate the project structure.

```bash
scaffold vs
```

## Commands & Examples

### scaffold ca

Scaffold a new Clean Architecture project.

```bash
scaffold ca --name my-project
```

```bash
scaffold ca --name my-project --dry-run
```

### scaffold gm

Scaffold a Pydantic v2 domain model, its gateway (an empty abstract repository contract), and test stubs.

```bash
scaffold gm --name order
```

Generated structure:

```text
domain/model/order/
├── __init__.py
├── order.py
└── gateways/
    ├── __init__.py
    └── order_repository.py
```

```bash
scaffold gm --name order --dry-run
```

### scaffold guc

Scaffold a use case in `domain/usecase/`. The module is always named `<name>_usecase.py` and the class `<Name>UseCase`. Writing `_usecase` in `--name` is optional and the suffix is never duplicated: `create_order`, `create_order_usecase` and `create_order_use_case` all create `create_order_usecase.py` with `CreateOrderUseCase`.

Use `--uses` with one or more **domain gateway** names (comma-separated) to generate a typed constructor and a wireup factory under `application/config/usecases/`. Gateway names must match ABCs in `domain/model/*/gateways/`. Helpers and adapters are not valid `--uses` targets.

```bash
scaffold guc --name create_order
```

```bash
scaffold guc --name create_order --uses order_repository
```

```bash
scaffold guc --name create_order --dry-run
```

### scaffold gda

Scaffold a driven adapter such as an HTTP client, secrets adapter, or generic outbound adapter.

Use `--gateway` with a domain gateway ABC name so the adapter is registered as `@injectable(as_type=<Gateway>)` and wired to that port.

```bash
scaffold gda --type rest-consumer
```

```bash
scaffold gda --type generic --name order_repository_adapter --gateway order_repository
```

```bash
scaffold gda --type generic --name my_adapter --dry-run
```

### scaffold gep

Scaffold an entry-point adapter for REST APIs, A2A agents, MCP servers, or generic entry points.

```bash
scaffold gep --type restapi
```

```bash
scaffold gep --type mcp --with-resources --with-prompts --dry-run
```

```bash
scaffold gep --type mcp --add-tool --name create_file --param path:str --param content:str --returns str --description "Creates a file on disk"
```

### scaffold gh

Scaffold a helper utility module and its test stub.

```bash
scaffold gh --name json_parser
```

```bash
scaffold gh --name json_parser --dry-run
```

### scaffold gpipe

Scaffold a CI/CD pipeline configuration for GitHub Actions or Azure Pipelines.

```bash
scaffold gpipe --provider github
```

```bash
scaffold gpipe --provider azure --dry-run
```

### scaffold vs

Scan the project for Clean Architecture import violations.

```bash
scaffold vs
```

```bash
scaffold vs --dry-run
```

### scaffold dm

Delete a previously generated module and its mirrored test file.

```bash
scaffold dm --name order
```

```bash
scaffold dm --name order --dry-run
```

### scaffold up

Update project dependencies using `uv lock --upgrade` and `uv sync`.

```bash
scaffold up --dry-run
```

```bash
scaffold update-project --dry-run
```

## Dependency injection (wireup)

New projects generated with `scaffold ca` use [wireup](https://pypi.org/project/wireup/) for async-first dependency injection:

- `application/config/wiring.py` defines `create_container()` and package scan targets (`driven_adapters`, `helpers`, `usecases`).
- Use cases declare gateway dependencies with `scaffold guc --uses …`; adapters bind to gateways with `scaffold gda --gateway …`.
- Entry points inject use cases with `Injected[…]` (REST/MCP) or resolve types from the container (agent/generic)—without importing `application` from infrastructure.
- Generated code enables ruff rule `ASYNC` and pytest `asyncio_mode = auto`.

**Legacy projects** (generated with scaffold-ca-python ≤ 0.5.0, `dependency-injector`, no `scaffold_version` in `[tool.scaffold-ca-python]`) are not modified by generate commands. Migrate to wireup manually, then set `scaffold_version` in `pyproject.toml` before using newer scaffold commands on that repo.

## Technologies

| Tool / Library | Version | Role |
|----------------|---------|------|
| Python | >=3.13 | Runtime |
| wireup | 2.13.0 | DI in generated projects |
| uv | latest | Dependency management, build, and publish |
| Typer | >=0.27.2 | CLI framework |
| Rich | >=15.0.0 | Terminal output formatting |
| Jinja2 | >=3.1 | Template engine for code generation |
| Pydantic v2 | >=2.0 | Runtime validation of template context |
| hatchling | latest | Build backend |
| uv-dynamic-versioning | latest | PEP 440 versioning from git tags |
| ruff | latest | Linting and formatting |
| mypy | latest (strict) | Static type checking |
| pytest + pytest-cov | latest | Test execution and coverage gating |

## Current Features

- Generates full Clean Architecture project skeletons with `scaffold ca`.
- Generates domain models with `scaffold gm`.
- Generates domain use cases with `scaffold guc` (optional `--uses` for gateway wiring and DI factories).
- Generates driven adapters with `scaffold gda` (optional `--gateway` for port binding).
- Generates entry points for REST API, agent, MCP, and generic modes with `scaffold gep`.
- Generates helper utilities with `scaffold gh`.
- Generates CI/CD pipeline files with `scaffold gpipe`.
- Validates import boundaries with `scaffold vs`.
- Deletes generated modules safely with `scaffold dm`.
- Updates project dependencies with `scaffold up`.
- Supports `--dry-run` previews across commands.
- Uses Jinja2 templates for all generated code.
- Validates template context with Pydantic v2.
- Formats terminal output with Rich.
- Enforces static checks with mypy strict and ruff.
- Maintains an 80%+ coverage gate with pytest-cov.

## Contributing

1. Fork the upstream repository on GitHub: https://github.com/bancolombia/scaffold-clean-architecture-py
2. Clone your fork.

```bash
git clone https://github.com/YOUR-USER/scaffold-clean-architecture-py.git
cd scaffold-clean-architecture-py
```

3. Set up the development environment.

```bash
uv sync
```

4. Create a feature branch.

```bash
git checkout -b your-branch-feature-name
```

5. Run the test suite.

```bash
uv run pytest
```

6. Check linting.

```bash
uv run ruff check src tests
```

7. Check types.

```bash
uv run mypy src
```

8. Commit your changes and open a pull request.

## License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for the full text.
