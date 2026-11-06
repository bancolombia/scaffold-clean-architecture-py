"""Parametrized end-to-end quality checks on generated projects."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from tests.e2e.conftest import run_quality_checks, scaffold_in

pytestmark = pytest.mark.e2e


def _src_pkg(project: Path) -> Path:
    """Return the single Python package directory under ``src/``."""
    pkgs = [p for p in (project / "src").iterdir() if p.is_dir() and p.name != "tests"]
    assert len(pkgs) == 1, f"expected one src package, found {pkgs}"
    return pkgs[0]


def _bootstrap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str = "myapp") -> Path:
    monkeypatch.chdir(tmp_path)
    result = scaffold_in(tmp_path, "ca", "--name", name)
    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]
    project = tmp_path / name
    monkeypatch.chdir(project)
    return project


def _run(project: Path, *args: str) -> None:
    result = scaffold_in(project, *args)
    assert result.exit_code == 0, result.output  # type: ignore[attr-defined]


def _scenario_01_restapi_swagger(project: Path, tmp_path: Path) -> None:
    spec = tmp_path / "api.yaml"
    spec.write_text(
        "openapi: '3.0.0'\ninfo:\n  title: T\n  version: '1'\npaths:\n"
        "  /items:\n    get:\n      responses:\n        '200':\n          description: OK\n",
        encoding="utf-8",
    )
    _run(project, "gep", "--type", "restapi", "--swagger", str(spec))
    controller = _src_pkg(project) / "infrastructure" / "entry_points" / "api" / "v1" / "rest_controller.py"
    body = controller.read_text(encoding="utf-8")
    assert '"/items"' in body and '"/health"' in body


def _scenario_02_agent_kafka_mcp(project: Path) -> None:
    _run(project, "gep", "--type", "agent", "--enable-kafka", "--enable-mcp-client")


def _scenario_03_generic_minimal(project: Path) -> None:
    _run(project, "gep", "--type", "generic")


def _scenario_04_module_usecase_adapter(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "guc", "--name", "create_order", "--uses", "order_repository")
    # Before the gateway adapter exists, the generated test must be xfail.
    uc_test = _src_pkg(project).parent / "tests" / "application" / "usecases" / "test_create_order_usecase.py"
    assert uc_test.exists(), "guc --uses must generate a test file"
    assert "xfail" in uc_test.read_text(encoding="utf-8"), (
        "guc --uses must mark the usecase test as xfail before the gateway adapter exists"
    )
    _run(
        project,
        "gda",
        "--type",
        "generic",
        "--name",
        "order_repository_adapter",
        "--gateway",
        "order_repository",
    )


def _scenario_05_rest_consumer_no_gateway(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "guc", "--name", "create_order")
    _run(project, "gda", "--type", "rest-consumer")


def _scenario_06_rest_consumer_with_gateway(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "guc", "--name", "create_order")
    _run(project, "gda", "--type", "rest-consumer", "--gateway", "order_repository")


def _scenario_07_adapter_before_usecase(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "gda", "--type", "rest-consumer")
    _run(project, "guc", "--name", "create_order", "--uses", "order_repository")


def _scenario_08_mcp_full(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "guc", "--name", "create_order")
    _run(project, "gda", "--type", "rest-consumer")
    _run(project, "gep", "--type", "mcp")


def _scenario_09_mcp_add_tool(project: Path) -> None:
    _scenario_08_mcp_full(project)
    _run(project, "gep", "--type", "mcp", "--add-tool", "--name", "my_tool", "--param", "query:str")


def _scenario_10_delete_module_conftest(project: Path) -> None:
    _run(project, "gm", "--name", "order")
    _run(project, "gda", "--type", "rest-consumer", "--gateway", "order_repository")
    conftest = project / "src" / "tests" / "conftest.py"
    assert conftest.exists(), "gda rest-consumer must create conftest.py"
    # Delete the domain module; the rest-consumer conftest.py must survive intact.
    _run(project, "dm", "--name", "order", "--confirm")
    assert conftest.exists(), "conftest.py must survive after dm order"
    assert "rest_consumer_env" in conftest.read_text(encoding="utf-8"), (
        "conftest.py must still contain the rest_consumer_env fixture after dm"
    )


_SCENARIOS: dict[str, Callable[..., None]] = {
    "01_restapi_swagger": _scenario_01_restapi_swagger,
    "02_agent_kafka_mcp": _scenario_02_agent_kafka_mcp,
    "03_generic_minimal": _scenario_03_generic_minimal,
    "04_module_usecase_adapter": _scenario_04_module_usecase_adapter,
    "05_rest_consumer_no_gateway": _scenario_05_rest_consumer_no_gateway,
    "06_rest_consumer_with_gateway": _scenario_06_rest_consumer_with_gateway,
    "07_adapter_before_usecase": _scenario_07_adapter_before_usecase,
    "08_mcp_full": _scenario_08_mcp_full,
    "09_mcp_add_tool": _scenario_09_mcp_add_tool,
    "10_delete_module_conftest": _scenario_10_delete_module_conftest,
}


@pytest.mark.parametrize("scenario_id", list(_SCENARIOS))
def test_generated_project_quality(
    scenario_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    uv_sync_project: Callable[[Path], None],
) -> None:
    project = _bootstrap(tmp_path, monkeypatch)
    handler = _SCENARIOS[scenario_id]
    if scenario_id == "01_restapi_swagger":
        handler(project, tmp_path)
    else:
        handler(project)
    uv_sync_project(project)
    run_quality_checks(project)
