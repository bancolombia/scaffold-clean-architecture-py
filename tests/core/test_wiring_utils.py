"""Tests for the MISSING_ADAPTERS marker helpers in core/wiring_utils.py."""

from __future__ import annotations

import textwrap
from pathlib import Path

from scaffold_ca_python.core.wiring_utils import (
    find_missing_adapters,
    remove_test_function,
    sync_missing_adapters_marker,
)

_PKG = "demo"

_FACTORY = """import wireup

from demo.domain.model.book.gateways.book_repository import BookRepository

@wireup.injectable
def f(book_repository: BookRepository) -> int:
    return 1
"""

_ADAPTER = """import wireup

@wireup.injectable(as_type=BookRepository)
class A:
    pass
"""

_WIRING_TEST = """import pytest

MISSING_ADAPTERS: list[str] = []

pytestmark = pytest.mark.xfail(bool(MISSING_ADAPTERS))
"""


def _write(root: Path, rel: str, content: str) -> None:
    path = root / "src" / _PKG / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_find_missing_adapters_lists_unimplemented_gateway(tmp_path: Path) -> None:
    _write(tmp_path, "application/config/usecases/book_usecase.py", _FACTORY)
    assert find_missing_adapters(tmp_path / "src" / _PKG) == ["BookRepository"]


def test_find_missing_adapters_empty_when_adapter_exists(tmp_path: Path) -> None:
    _write(tmp_path, "application/config/usecases/book_usecase.py", _FACTORY)
    _write(tmp_path, "infrastructure/driven_adapters/book/adapter.py", _ADAPTER)
    assert find_missing_adapters(tmp_path / "src" / _PKG) == []


def test_find_missing_adapters_without_project_dirs(tmp_path: Path) -> None:
    assert find_missing_adapters(tmp_path / "src" / _PKG) == []


def test_sync_marker_rewrites_list(tmp_path: Path) -> None:
    path = tmp_path / "test_wiring.py"
    path.write_text(_WIRING_TEST, encoding="utf-8")
    assert sync_missing_adapters_marker(path, ["BookRepository"]) is True
    assert 'MISSING_ADAPTERS: list[str] = ["BookRepository"]' in path.read_text()
    assert "pytestmark" in path.read_text()


def test_sync_marker_is_idempotent_and_clears(tmp_path: Path) -> None:
    path = tmp_path / "test_wiring.py"
    path.write_text(_WIRING_TEST, encoding="utf-8")
    sync_missing_adapters_marker(path, ["B", "A"])
    assert 'MISSING_ADAPTERS: list[str] = ["A", "B"]' in path.read_text()
    assert sync_missing_adapters_marker(path, ["A", "B"]) is False
    assert sync_missing_adapters_marker(path, []) is True
    assert "MISSING_ADAPTERS: list[str] = []" in path.read_text()


def test_remove_test_function_strips_decorators() -> None:
    src = textwrap.dedent("""\
        @pytest.mark.usefixtures("x")
        def test_foo() -> None:
            assert True

        def test_bar() -> None:
            assert False
    """)
    result = remove_test_function(src, "test_foo")
    assert result is not None
    assert "@pytest.mark.usefixtures" not in result
    assert "test_bar" in result


def test_sync_marker_noop_without_marker_or_file(tmp_path: Path) -> None:
    path = tmp_path / "test_wiring.py"
    assert sync_missing_adapters_marker(path, ["X"]) is False
    path.write_text("def test_x() -> None: ...\n", encoding="utf-8")
    assert sync_missing_adapters_marker(path, ["X"]) is False
    assert path.read_text() == "def test_x() -> None: ...\n"
