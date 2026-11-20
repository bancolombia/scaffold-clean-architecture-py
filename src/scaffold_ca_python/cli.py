import typer

from scaffold_ca_python.commands import (
    delete_module,
    generate_driven_adapter,
    generate_entry_point,
    generate_helper,
    generate_model,
    generate_pipeline,
    generate_project,
    generate_use_case,
    install_skill,
    update_project,
    validate_structure,
)

app = typer.Typer(
    name="scaffold-ca-python",
    help="Scaffold production-ready Clean Architecture Python projects.",
    add_completion=False,
    rich_markup_mode="rich",
)

_COMMAND_MODULES = (
    generate_project,
    generate_model,
    generate_use_case,
    generate_driven_adapter,
    generate_entry_point,
    generate_helper,
    generate_pipeline,
    update_project,
    install_skill,
    delete_module,
    validate_structure,
)

for _mod in _COMMAND_MODULES:
    _mod.register(app)


@app.callback(invoke_without_command=True)
def _main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(0)
