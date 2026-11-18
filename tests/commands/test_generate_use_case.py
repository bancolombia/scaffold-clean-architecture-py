"""Tests for guc / generate-use-case command."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.helpers import strip_ansi

runner = CliRunner()

# Fixtures

# Success path


def test_creates_use_case_file(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "domain" / "usecase" / "create_order_usecase.py").exists()


def test_creates_test_mirror(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "tests" / "domain" / "usecase" / "test_create_order_usecase.py").exists()


def test_use_case_file_contains_async_execute(project_root: Path) -> None:
    runner.invoke(app, ["guc", "--name", "place_order"], catch_exceptions=False)
    content = (project_root / "src" / "my_app" / "domain" / "usecase" / "place_order_usecase.py").read_text()
    assert "async def execute" in content


def test_use_case_file_contains_class(project_root: Path) -> None:
    runner.invoke(app, ["guc", "--name", "place_order"], catch_exceptions=False)
    content = (project_root / "src" / "my_app" / "domain" / "usecase" / "place_order_usecase.py").read_text()
    assert "class PlaceOrderUseCase:" in content


def test_success_message_reports_class_name(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "place_order"], catch_exceptions=False)
    assert "PlaceOrderUseCase" in result.output


def test_test_file_contains_pytest_stub(project_root: Path) -> None:
    runner.invoke(app, ["guc", "--name", "place_order"], catch_exceptions=False)
    content = (project_root / "src" / "tests" / "domain" / "usecase" / "test_place_order_usecase.py").read_text()
    assert "def test_" in content


def test_generate_use_case_alias_works(project_root: Path) -> None:
    result = runner.invoke(app, ["generate-use-case", "--name", "cancel_order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "domain" / "usecase" / "cancel_order_usecase.py").exists()


# Dry-run


def test_dry_run_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (project_root / "src" / "my_app" / "domain" / "usecase" / "create_order_usecase.py").exists()


def test_dry_run_prints_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order", "--dry-run"], catch_exceptions=False)
    assert "create_order" in result.output.lower()


# Error cases


def test_duplicate_use_case_exits_1(project_root: Path) -> None:
    runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    result = runner.invoke(app, ["guc", "--name", "create_order"])
    assert result.exit_code == 1


# : no-args → help


# : suffix is never duplicated


def test_all_spellings_produce_identical_output(project_root: Path) -> None:
    src = project_root / "src" / "my_app" / "domain" / "usecase" / "book_usecase.py"
    test = project_root / "src" / "tests" / "domain" / "usecase" / "test_book_usecase.py"
    collected: list[tuple[str, str]] = []
    for spelling in ("book", "book_usecase", "book_use_case", "book_usecase_usecase", "book_use_case_usecase"):
        result = runner.invoke(app, ["guc", "--name", spelling], catch_exceptions=False)
        assert result.exit_code == 0
        content = src.read_text()
        assert "class BookUseCase:" in content
        assert "BookUsecaseUseCase" not in content
        collected.append((content, test.read_text()))
        src.unlink()
        test.unlink()
    assert all(pair == collected[0] for pair in collected)


def test_suffixed_name_creates_single_suffix_module(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order_usecase"], catch_exceptions=False)
    assert result.exit_code == 0
    path = project_root / "src" / "my_app" / "domain" / "usecase" / "create_order_usecase.py"
    assert "class CreateOrderUseCase:" in path.read_text()


def test_suffix_word_elsewhere_is_preserved(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "usecase_registry"], catch_exceptions=False)
    assert result.exit_code == 0
    path = project_root / "src" / "my_app" / "domain" / "usecase" / "usecase_registry_usecase.py"
    assert "class UsecaseRegistryUseCase:" in path.read_text()


@pytest.mark.parametrize("name", ["usecase", "use_case", "usecase_usecase"])
def test_suffix_only_name_exits_1(project_root: Path, name: str) -> None:
    result = runner.invoke(app, ["guc", "--name", name])
    out = strip_ansi(result.output)
    assert result.exit_code == 1
    assert "is only the 'usecase' suffix" in out
    assert "create_order" in out
    assert not list((project_root / "src" / "my_app" / "domain" / "usecase").glob("*_usecase.py"))


# : dry-run and conflict detection use the normalized name


def _usecase_dir(root: Path) -> Path:
    return root / "src" / "my_app" / "domain" / "usecase"


def test_dry_run_with_suffixed_name_lists_normalized_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["guc", "--name", "create_order_usecase", "--dry-run"], catch_exceptions=False)
    out = strip_ansi(result.output)
    assert result.exit_code == 0
    assert "create_order_usecase (dry run)" in out
    assert "create_order_usecase.py" in out
    assert "test_create_order_usecase.py" in out
    assert "create_order_usecase_usecase" not in out
    assert not (_usecase_dir(project_root) / "create_order_usecase.py").exists()


def test_dry_run_paths_match_real_run(project_root: Path) -> None:
    dry = strip_ansi(runner.invoke(app, ["guc", "--name", "create_order", "--dry-run"]).output)
    runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    created = [
        _usecase_dir(project_root) / "create_order_usecase.py",
        project_root / "src" / "tests" / "domain" / "usecase" / "test_create_order_usecase.py",
    ]
    assert all(p.exists() for p in created)
    assert all(p.name in dry for p in created)


@pytest.mark.parametrize("again", ["create_order", "create_order_usecase", "create_order_use_case"])
def test_existing_use_case_blocks_every_spelling(project_root: Path, again: str) -> None:
    runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    path = _usecase_dir(project_root) / "create_order_usecase.py"
    path.write_text("# edited\n")
    result = runner.invoke(app, ["guc", "--name", again])
    assert result.exit_code == 1
    assert "already exists" in " ".join(strip_ansi(result.output).split())
    assert path.read_text() == "# edited\n"


def test_existing_test_file_blocks_generation(project_root: Path) -> None:
    test_file = project_root / "src" / "tests" / "domain" / "usecase" / "test_create_order_usecase.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("# mine\n")
    result = runner.invoke(app, ["guc", "--name", "create_order"])
    assert result.exit_code == 1
    assert "already exists" in " ".join(strip_ansi(result.output).split())
    assert not (_usecase_dir(project_root) / "create_order_usecase.py").exists()
    assert test_file.read_text() == "# mine\n"


def test_legacy_file_is_ignored(project_root: Path) -> None:
    legacy = _usecase_dir(project_root) / "create_order.py"
    legacy.write_text("# legacy\n")
    result = runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "legacy" not in strip_ansi(result.output).lower().replace("# legacy", "")
    assert (_usecase_dir(project_root) / "create_order_usecase.py").exists()
    assert legacy.read_text() == "# legacy\n"


#  (): guc --uses option (write first — must FAIL before –)


def test_guc_uses_creates_factory_file(project_with_order_model: Path) -> None:
    """--uses should create application/config/usecases/<name>_usecase.py factory."""
    result = runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    assert result.exit_code == 0
    factory_path = (
        project_with_order_model / "src" / "my_app" / "application" / "config" / "usecases" / "create_order_usecase.py"
    )
    assert factory_path.exists(), "Factory file must be created when --uses is provided"


def test_guc_uses_factory_has_typed_params(project_with_order_model: Path) -> None:
    """factory file must inject the named gateways as typed parameters."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    factory_path = (
        project_with_order_model / "src" / "my_app" / "application" / "config" / "usecases" / "create_order_usecase.py"
    )
    content = factory_path.read_text()
    assert "OrderRepository" in content, "Factory must reference the typed gateway"
    assert "order_repository" in content, "Factory must include the gateway param"


def test_guc_without_uses_no_factory_file(project_root: Path) -> None:
    """without --uses, generate-use-case must NOT create a factory file."""
    runner.invoke(app, ["guc", "--name", "create_order"], catch_exceptions=False)
    usecases_dir = project_root / "src" / "my_app" / "application" / "config" / "usecases"
    factory = usecases_dir / "create_order_usecase.py"
    assert not factory.exists(), "No factory file without --uses"


def test_guc_uses_gateway_not_found_exits_nonzero(project_root: Path) -> None:
    """--uses with unknown gateway name must exit non-zero."""
    result = runner.invoke(app, ["guc", "--name", "create_order", "--uses", "nonexistent_gateway"])
    assert result.exit_code != 0


def test_guc_uses_helper_name_exits_with_infra_hint(project_root: Path, tmp_path: Path) -> None:
    """--uses with a helper name must exit non-zero with an infra-only hint."""
    runner.invoke(app, ["gh", "--name", "log_helper"], catch_exceptions=False)
    result = runner.invoke(app, ["guc", "--name", "create_order", "--uses", "log_helper"])
    assert result.exit_code != 0
    out = strip_ansi(result.output).lower()
    assert "infrastructure" in out or "helper" in out, "Must hint that helpers are infrastructure-only"


# : guc --uses factory test + wiring append


def test_guc_uses_creates_factory_test_file(project_with_order_model: Path) -> None:
    """--uses must also create tests/application/config/usecases/test_<name>_usecase.py."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    test_path = (
        project_with_order_model
        / "src"
        / "tests"
        / "application"
        / "config"
        / "usecases"
        / "test_create_order_usecase.py"
    )
    assert test_path.exists(), "Factory test file must be created when --uses is provided"
    content = test_path.read_text()
    assert "create_order_usecase_factory" in content
    assert "isinstance" in content


def test_guc_uses_appends_wiring_test(project_with_order_model: Path) -> None:
    """--uses must append a test function to test_wiring.py."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    wiring_test = project_with_order_model / "src" / "tests" / "application" / "config" / "test_wiring.py"
    assert wiring_test.exists()
    content = wiring_test.read_text()
    assert "test_container_resolves_create_order_usecase" in content


def test_guc_uses_wiring_append_is_idempotent(project_with_order_model: Path) -> None:
    """Running guc --uses twice must not duplicate the wiring test function."""
    wiring_test = project_with_order_model / "src" / "tests" / "application" / "config" / "test_wiring.py"
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    after_first = wiring_test.read_text()
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"])
    after_second = wiring_test.read_text()
    assert after_second == after_first
    assert after_second.count("test_container_resolves_create_order_usecase") == 1


def test_guc_uses_hint_when_no_adapter(project_with_order_model: Path) -> None:
    """guc --uses must warn when no adapter implements the gateway."""
    result = runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    assert result.exit_code == 0
    out = strip_ansi(result.output)
    assert "No adapter implements" in out or "OrderRepository" in out


#  /  /  / : .2 — green suite before any adapter exists


def _wiring_test_path(root: Path) -> Path:
    return root / "src" / "tests" / "application" / "config" / "test_wiring.py"


def test_ca_wiring_test_has_empty_marker_and_strict_xfail(project_root: Path) -> None:
    """ca generates MISSING_ADAPTERS (empty) and a strict module-level xfail."""
    content = _wiring_test_path(project_root).read_text()
    assert "MISSING_ADAPTERS: list[str] = []" in content
    assert "pytestmark = pytest.mark.xfail(" in content
    assert "strict=True" in content
    assert "raises=WireupError" in content
    assert "no registered use cases yet" not in content


def test_guc_uses_without_adapter_sets_missing_adapters(project_with_order_model: Path) -> None:
    """guc --uses with no adapter lists the gateway in MISSING_ADAPTERS."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    content = _wiring_test_path(project_with_order_model).read_text()
    assert 'MISSING_ADAPTERS: list[str] = ["OrderRepository"]' in content


def test_gda_gateway_clears_missing_adapters_and_appends_awaited_stub(project_with_order_model: Path) -> None:
    """gda --gateway empties the list and appends a stub that awaits the gateway."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    result = runner.invoke(
        app,
        ["gda", "--type", "generic", "--name", "order_repository_adapter", "--gateway", "order_repository"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    content = _wiring_test_path(project_with_order_model).read_text()
    assert "MISSING_ADAPTERS: list[str] = []" in content
    assert "async def test_container_resolves_order_repository_adapter" in content
    assert "await container.get(OrderRepository)" in content


def test_gda_gateway_wiring_stub_is_idempotent_and_dm_removes_it(project_with_order_model: Path) -> None:
    """dm on the adapter removes its wiring test and restores MISSING_ADAPTERS."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    runner.invoke(
        app,
        ["gda", "--type", "generic", "--name", "order_repository_adapter", "--gateway", "order_repository"],
        catch_exceptions=False,
    )
    runner.invoke(app, ["dm", "--name", "order_repository_adapter", "--confirm"], catch_exceptions=False)
    content = _wiring_test_path(project_with_order_model).read_text()
    assert "test_container_resolves_order_repository_adapter" not in content
    assert 'MISSING_ADAPTERS: list[str] = ["OrderRepository"]' in content


def test_generated_use_case_tests_have_no_type_ignore(project_with_order_model: Path) -> None:
    """generated tests must not carry unused `type: ignore` comments."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    root = project_with_order_model / "src" / "tests"
    for path in (
        root / "domain" / "usecase" / "test_create_order_usecase.py",
        root / "application" / "config" / "usecases" / "test_create_order_usecase.py",
    ):
        assert "type: ignore" not in path.read_text(), path


def test_generated_config_and_factory_pass_ruff_format(project_with_order_model: Path) -> None:
    """blank line after module docstring in config.py and the factory."""
    runner.invoke(app, ["guc", "--name", "create_order", "--uses", "order_repository"], catch_exceptions=False)
    src = project_with_order_model / "src" / "my_app" / "application" / "config"
    for path in (src / "config.py", src / "usecases" / "create_order_usecase.py"):
        lines = path.read_text().splitlines()
        assert lines[0].startswith('"""') and lines[1] == "", path
