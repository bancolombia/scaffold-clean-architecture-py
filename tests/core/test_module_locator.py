"""Tests for find_module_targets ( / )."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.module_locator import find_module_targets


def _make_project(tmp_path: Path) -> Path:
    """Create a minimal src-layout scaffold project skeleton."""
    root = tmp_path / "my-proj"
    pkg = root / "src" / "my_proj"
    tests = root / "tests"
    (pkg / "domain" / "model").mkdir(parents=True)
    (pkg / "application" / "use_cases").mkdir(parents=True)
    (pkg / "infrastructure" / "driven_adapters").mkdir(parents=True)
    (pkg / "infrastructure" / "entry_points").mkdir(parents=True)
    (pkg / "utils").mkdir(parents=True)
    tests.mkdir(parents=True)
    return root


def test_model_with_test_returns_src_and_test(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pkg_dir = root / "src" / "my_proj"
    tests_dir = root / "tests"
    model_file = pkg_dir / "domain" / "model" / "order.py"
    test_file = tests_dir / "domain" / "model" / "test_order.py"
    model_file.touch()
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.touch()

    results = find_module_targets(root, root / "src" / "my_proj", "order")
    assert (model_file, test_file) in results


def test_adapter_without_test_returns_dir_none(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pkg_dir = root / "src" / "my_proj"
    adapter_dir = pkg_dir / "infrastructure" / "driven_adapters" / "my_adapter"
    adapter_dir.mkdir()

    results = find_module_targets(root, root / "src" / "my_proj", "my_adapter")
    assert any(src == adapter_dir and t is None for src, t in results)


def test_no_match_returns_empty(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    results = find_module_targets(root, root / "src" / "my_proj", "nonexistent")
    assert results == []


def test_search_order_model_first(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pkg_dir = root / "src" / "my_proj"
    model_file = pkg_dir / "domain" / "model" / "thing.py"
    model_file.touch()

    results = find_module_targets(root, root / "src" / "my_proj", "thing")
    assert len(results) >= 1
    assert results[0][0] == model_file


def test_model_package_returns_dirs(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pkg_dir = root / "src" / "my_proj" / "domain" / "model" / "order"
    tests_dir = root / "tests" / "domain" / "model" / "order"
    pkg_dir.mkdir()
    tests_dir.mkdir(parents=True)

    assert (pkg_dir, tests_dir) in find_module_targets(root, root / "src" / "my_proj", "order")


def test_model_package_without_tests_returns_none(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pkg_dir = root / "src" / "my_proj" / "domain" / "model" / "order"
    pkg_dir.mkdir()

    assert (pkg_dir, None) in find_module_targets(root, root / "src" / "my_proj", "order")


def test_model_package_listed_before_legacy_flat(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    model_dir = root / "src" / "my_proj" / "domain" / "model"
    (model_dir / "order").mkdir()
    (model_dir / "order.py").touch()

    results = find_module_targets(root, root / "src" / "my_proj", "order")
    assert results[0][0] == model_dir / "order"


def _usecase_files(root: Path, name: str) -> tuple[Path, Path]:
    src = root / "src" / "my_proj" / "domain" / "usecase" / f"{name}.py"
    test = root / "tests" / "domain" / "usecase" / f"test_{name}.py"
    src.parent.mkdir(parents=True, exist_ok=True)
    test.parent.mkdir(parents=True, exist_ok=True)
    src.touch()
    test.touch()
    return src, test


def test_usecase_found_by_base_and_suffixed_name(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    pair = _usecase_files(root, "book_usecase")

    assert pair in find_module_targets(root, root / "src" / "my_proj", "book")
    assert pair in find_module_targets(root, root / "src" / "my_proj", "book_usecase")


def test_usecase_listed_once_for_suffixed_name(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    src, _ = _usecase_files(root, "book_usecase")

    results = find_module_targets(root, root / "src" / "my_proj", "book_usecase")
    assert [s for s, _t in results].count(src) == 1


def test_usecase_both_layouts_new_first(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    new = _usecase_files(root, "book_usecase")
    legacy = _usecase_files(root, "book")

    results = find_module_targets(root, root / "src" / "my_proj", "book")
    assert results[:2] == [new, legacy]


def test_legacy_usecase_still_found(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    legacy = _usecase_files(root, "book")

    assert find_module_targets(root, root / "src" / "my_proj", "book") == [legacy]


def test_suffix_only_name_returns_empty(tmp_path: Path) -> None:
    root = _make_project(tmp_path)
    assert find_module_targets(root, root / "src" / "my_proj", "usecase") == []
