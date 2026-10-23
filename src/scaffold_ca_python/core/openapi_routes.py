"""Parse OpenAPI YAML/JSON files into (path, method) route lists."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

_HTTP_METHODS: frozenset[str] = frozenset({"get", "post", "put", "patch", "delete", "head", "options"})


def parse_routes(path: Path) -> list[tuple[str, str]]:
    """Return ``(route_path, method)`` pairs from an OpenAPI spec file.

    Returns an empty list when the file has no valid paths section.
    """
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in (".yaml", ".yml"):
        raw: object = yaml.safe_load(text)
    else:
        raw = json.loads(text)
    if not isinstance(raw, dict):
        return []
    paths_value = raw.get("paths", {})
    if not isinstance(paths_value, dict):
        return []
    result: list[tuple[str, str]] = []
    for route_path, methods in paths_value.items():
        if isinstance(methods, dict):
            for method in methods:
                if method.lower() in _HTTP_METHODS:
                    result.append((str(route_path), method.lower()))
    return result
