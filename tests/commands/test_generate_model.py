"""Tests for gm / generate-model command (T034)."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app
from tests.conftest import strip_ansi

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Bootstrap a minimal CA project root that generate-model can work inside."""
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["ca", "--name", "my-app"], catch_exceptions=False)
    assert result.exit_code == 0
    project_dir = tmp_path / "my-app"
    monkeypatch.chdir(project_dir)
    return project_dir


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


def test_creates_model_file(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "domain" / "model" / "order" / "order.py").exists()


def test_creates_test_mirror(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "tests" / "domain" / "model" / "order" / "test_order.py").exists()


def test_model_file_contains_pydantic_basemodel(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "product"], catch_exceptions=False)
    content = (project_root / "src" / "my_app" / "domain" / "model" / "product" / "product.py").read_text()
    assert "BaseModel" in content
    assert "Product" in content


def test_test_file_contains_pytest_stub(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "product"], catch_exceptions=False)
    content = (project_root / "src" / "tests" / "domain" / "model" / "product" / "test_product.py").read_text()
    assert "def test_" in content


def test_generate_model_alias_works(project_root: Path) -> None:
    result = runner.invoke(app, ["generate-model", "--name", "invoice"], catch_exceptions=False)
    assert result.exit_code == 0
    assert (project_root / "src" / "my_app" / "domain" / "model" / "invoice" / "invoice.py").exists()


# ---------------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------------


def test_dry_run_writes_nothing(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order", "--dry-run"], catch_exceptions=False)
    assert result.exit_code == 0
    assert not (project_root / "src" / "my_app" / "domain" / "model" / "order").exists()
    assert not (project_root / "src" / "tests" / "domain" / "model" / "order").exists()


def test_dry_run_prints_paths(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order", "--dry-run"], catch_exceptions=False)
    assert "order" in result.output.lower()


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


def test_existing_package_dir_exits_1(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    result = runner.invoke(app, ["gm", "--name", "order"])
    assert result.exit_code == 1
    out = strip_ansi(result.output).replace("\n", "")
    assert "Directory 'src/my_app/domain/model/order/' already exists." in out
    assert "Hint:" in out


def test_legacy_flat_model_exits_1(project_root: Path) -> None:
    model_dir = project_root / "src" / "my_app" / "domain" / "model"
    (model_dir / "order.py").write_text("", encoding="utf-8")
    result = runner.invoke(app, ["gm", "--name", "order"])
    assert result.exit_code == 1
    assert "File 'src/my_app/domain/model/order.py' already exists." in strip_ansi(result.output).replace("\n", "")
    assert not (model_dir / "order").exists()


def test_existing_tests_dir_exits_1(project_root: Path) -> None:
    (project_root / "src" / "tests" / "domain" / "model" / "order").mkdir(parents=True)
    result = runner.invoke(app, ["gm", "--name", "order"])
    assert result.exit_code == 1
    out = strip_ansi(result.output).replace("\n", "")
    assert "Directory 'src/tests/domain/model/order/' already exists." in out
    assert not (project_root / "src" / "my_app" / "domain" / "model" / "order").exists()


def test_invalid_name_exits_nonzero(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "1Bad"])
    assert result.exit_code != 0


def test_pascal_case_name_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "InvalidModel"])
    assert result.exit_code == 1
    assert "snake_case" in result.output


def test_kebab_name_exits_1(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "my-model"])
    assert result.exit_code == 1
    assert "snake_case" in result.output


def test_no_project_root_exits_1(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["gm", "--name", "order"])
    assert result.exit_code == 1


def test_snake_name_generates_pascal_class(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "my_model"], catch_exceptions=False)
    assert result.exit_code == 0
    content = (project_root / "src" / "my_app" / "domain" / "model" / "my_model" / "my_model.py").read_text()
    assert "class MyModel" in content


# ---------------------------------------------------------------------------
# US3: no-args → help (T018)
# ---------------------------------------------------------------------------


def test_gm_no_args_exits_0() -> None:
    result = runner.invoke(app, ["gm"])
    assert result.exit_code == 0


def test_gm_no_args_shows_name_option() -> None:
    result = runner.invoke(app, ["gm"])
    assert "--name" in strip_ansi(result.output)


# ---------------------------------------------------------------------------
# Gateway generation (025)
# ---------------------------------------------------------------------------


def test_creates_gateway_file(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    gw = project_root / "src" / "my_app" / "domain" / "model" / "order" / "gateways" / "order_repository.py"
    assert "class OrderRepository(ABC):" in gw.read_text()


def test_creates_package_inits(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    base = project_root / "src" / "my_app" / "domain" / "model" / "order"
    assert (base / "__init__.py").exists()
    assert (base / "gateways" / "__init__.py").exists()


def test_creates_gateway_test_mirror(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    path = project_root / "src" / "tests" / "domain" / "model" / "order" / "gateways" / "test_order_repository.py"
    assert path.exists()


def test_success_message_counts_six_files(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    assert "Created 6 file(s)." in strip_ansi(result.output)


def test_gateway_has_no_outward_imports(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    gw = project_root / "src" / "my_app" / "domain" / "model" / "order" / "gateways" / "order_repository.py"
    content = gw.read_text()
    for forbidden in ("infrastructure", "application", "domain.model.order.order"):
        assert forbidden not in content


def test_generated_model_passes_structure_validation(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "order"], catch_exceptions=False)
    result = runner.invoke(app, ["vs"], catch_exceptions=False)
    assert result.exit_code == 0
    assert "no violations" in result.output.lower()


def test_multi_word_name_layout(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "research_paper"], catch_exceptions=False)
    assert result.exit_code == 0
    base = project_root / "src" / "my_app" / "domain" / "model" / "research_paper"
    tbase = project_root / "src" / "tests" / "domain" / "model" / "research_paper"
    assert "class ResearchPaper(BaseModel)" in (base / "research_paper.py").read_text()
    assert "class ResearchPaperRepository(ABC):" in (base / "gateways" / "research_paper_repository.py").read_text()
    assert (base / "__init__.py").exists()
    assert (base / "gateways" / "__init__.py").exists()
    assert (tbase / "test_research_paper.py").exists()
    assert (tbase / "gateways" / "test_research_paper_repository.py").exists()


def test_generating_second_model_leaves_first_untouched(project_root: Path) -> None:
    runner.invoke(app, ["gm", "--name", "paper"], catch_exceptions=False)
    base = project_root / "src" / "my_app" / "domain" / "model" / "paper"
    before = {p: p.read_text() for p in base.rglob("*.py")}
    runner.invoke(app, ["gm", "--name", "research_paper"], catch_exceptions=False)
    assert {p: p.read_text() for p in base.rglob("*.py")} == before


def test_name_ending_in_repository(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "paper_repository"], catch_exceptions=False)
    assert result.exit_code == 0
    gw = project_root / "src" / "my_app" / "domain" / "model" / "paper_repository" / "gateways"
    assert (gw / "paper_repository_repository.py").exists()


def test_dry_run_lists_all_six_files(project_root: Path) -> None:
    result = runner.invoke(app, ["gm", "--name", "order", "--dry-run"], catch_exceptions=False)
    out = strip_ansi(result.output)
    for name in ("order_repository.py", "test_order_repository.py", "order.py", "test_order.py", "__init__.py"):
        assert name in out
    assert not (project_root / "src" / "my_app" / "domain" / "model" / "order").exists()
    assert not (project_root / "src" / "tests" / "domain" / "model" / "order").exists()
