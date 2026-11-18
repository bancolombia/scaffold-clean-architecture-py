"""Performance benchmark tests.

Covered: gm, guc, gda, gh complete within 3 s; scaffold vs completes in under 5 s on a project
with 200 Python files.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from scaffold_ca_python.cli import app

runner = CliRunner()

pytestmark = pytest.mark.benchmark

# Fixtures


@pytest.fixture()
def bench_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "bench-app"], catch_exceptions=False)
    project_dir = tmp_path / "bench-app"
    monkeypatch.chdir(project_dir)
    return project_dir


# : Generation commands under 3 s


def test_gm_performance(benchmark: pytest.fixture, bench_project: Path) -> None:  # type: ignore[type-arg]
    def run() -> None:
        result = runner.invoke(app, ["gm", "--name", "perf_model"], catch_exceptions=False)
        assert result.exit_code == 0
        # Cleanup so benchmark can repeat
        shutil.rmtree(bench_project / "src" / "bench_app" / "domain" / "model" / "perf_model", ignore_errors=True)
        shutil.rmtree(bench_project / "src" / "tests" / "domain" / "model" / "perf_model", ignore_errors=True)

    benchmark.pedantic(run, iterations=1, rounds=3)  # type: ignore[func-returns-value]
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 3.0  # type: ignore[index]


def test_guc_performance(benchmark: pytest.fixture, bench_project: Path) -> None:  # type: ignore[type-arg]
    def run() -> None:
        runner.invoke(app, ["guc", "--name", "perf"], catch_exceptions=False)
        src = bench_project / "src" / "bench_app" / "domain" / "usecase" / "perf_usecase.py"
        test = bench_project / "src" / "tests" / "domain" / "usecase" / "test_perf_usecase.py"
        src.unlink(missing_ok=True)
        test.unlink(missing_ok=True)

    benchmark.pedantic(run, iterations=1, rounds=3)
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 3.0  # type: ignore[index]


def test_gda_performance(benchmark: pytest.fixture, bench_project: Path) -> None:  # type: ignore[type-arg]
    import shutil

    def run() -> None:
        runner.invoke(app, ["gda", "--type", "rest-consumer"], catch_exceptions=False)
        src = bench_project / "src" / "bench_app" / "infrastructure" / "driven_adapters" / "rest_consumer"
        test = bench_project / "src" / "tests" / "infrastructure" / "driven_adapters" / "rest_consumer"
        if src.exists():
            shutil.rmtree(src)
        if test.exists():
            shutil.rmtree(test)

    benchmark.pedantic(run, iterations=1, rounds=3)
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 3.0  # type: ignore[index]


def test_gh_performance(benchmark: pytest.fixture, bench_project: Path) -> None:  # type: ignore[type-arg]
    import shutil

    def run() -> None:
        runner.invoke(app, ["gh", "--name", "PerfHelper"], catch_exceptions=False)
        src = bench_project / "src" / "bench_app" / "infrastructure" / "helpers" / "perf_helper"
        test = bench_project / "src" / "tests" / "infrastructure" / "helpers" / "perf_helper"
        if src.exists():
            shutil.rmtree(src)
        if test.exists():
            shutil.rmtree(test)

    benchmark.pedantic(run, iterations=1, rounds=3)
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 3.0  # type: ignore[index]


# : vs under 5 s on a project with 200 Python files


@pytest.fixture()
def large_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a CA project with 200 Python source files for vs benchmark."""
    monkeypatch.chdir(tmp_path)
    runner.invoke(app, ["ca", "--name", "large-app"], catch_exceptions=False)
    project_dir = tmp_path / "large-app"
    monkeypatch.chdir(project_dir)

    # Generate 200 stub Python files under domain/model/
    model_dir = project_dir / "src" / "large_app" / "domain" / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    for i in range(200):
        (model_dir / f"stub_{i:03d}.py").write_text(f'"""Stub module {i}."""\n\n\nclass Stub{i:03d}:\n    pass\n')
    return project_dir


def test_vs_performance_200_files(benchmark: pytest.fixture, large_project: Path) -> None:  # type: ignore[type-arg]
    def run() -> None:
        runner.invoke(app, ["vs"], catch_exceptions=False)

    benchmark.pedantic(run, iterations=1, rounds=3)
    if benchmark.stats is not None:
        assert benchmark.stats["mean"] < 5.0  # type: ignore[index]
