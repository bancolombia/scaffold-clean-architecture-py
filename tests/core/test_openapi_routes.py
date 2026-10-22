"""Tests for parse_routes (T034 / US4)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scaffold_ca_python.core.openapi_routes import parse_routes


def _write_yaml(path: Path, data: object) -> None:
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def test_yaml_with_get_and_post(tmp_path: Path) -> None:
    f = tmp_path / "api.yaml"
    _write_yaml(f, {"paths": {"/x": {"get": {}, "post": {}}}})
    result = parse_routes(f)
    assert ("/x", "get") in result
    assert ("/x", "post") in result


def test_json_spec(tmp_path: Path) -> None:
    f = tmp_path / "api.json"
    _write_json(f, {"paths": {"/items": {"delete": {}}}})
    result = parse_routes(f)
    assert ("/items", "delete") in result


def test_non_dict_root_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "bad.yaml"
    _write_yaml(f, ["not", "a", "dict"])
    assert parse_routes(f) == []


def test_non_dict_paths_returns_empty(tmp_path: Path) -> None:
    f = tmp_path / "bad2.yaml"
    _write_yaml(f, {"paths": "not-a-dict"})
    assert parse_routes(f) == []


def test_non_http_methods_ignored(tmp_path: Path) -> None:
    f = tmp_path / "api.yaml"
    _write_yaml(f, {"paths": {"/x": {"get": {}, "parameters": []}}})
    result = parse_routes(f)
    assert ("/x", "get") in result
    assert ("/x", "parameters") not in result
