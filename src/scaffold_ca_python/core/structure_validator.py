"""StructureValidator: AST-based Clean Architecture import checker."""

from __future__ import annotations

import ast
import warnings
from pathlib import Path

from scaffold_ca_python.core.errors import ScaffoldError
from scaffold_ca_python.models.layer import FORBIDDEN_IMPORTS, Layer
from scaffold_ca_python.models.violation import ValidationReport, Violation

_PATH_SEGMENTS_TO_LAYER: list[tuple[tuple[str, ...], Layer]] = [
    (("domain", "model"), Layer.DOMAIN_MODEL),
    (("domain", "usecase"), Layer.DOMAIN_USECASE),
    (("infrastructure", "entry_points"), Layer.ENTRY_POINTS),
    (("infrastructure", "driven_adapters"), Layer.DRIVEN_ADAPTERS),
    (("infrastructure", "helpers"), Layer.HELPERS),
    (("application",), Layer.APPLICATION),
]


def _layer_from_path_parts(parts: tuple[str, ...]) -> Layer | None:
    """Return the Layer for *parts* (relative to the package root), or None."""
    for segments, layer in _PATH_SEGMENTS_TO_LAYER:
        n = len(segments)
        if len(parts) >= n and parts[:n] == segments:
            return layer
    return None


def _layer_from_module(module: str, python_package: str) -> Layer | None:
    """Return the Layer that *module* belongs to, or None if not project-internal."""
    parts = tuple(module.split("."))
    if not parts or parts[0] != python_package:
        return None
    return _layer_from_path_parts(parts[1:])


def _make_hint(source: Layer, target: Layer) -> str:
    if source in (Layer.DOMAIN_MODEL, Layer.DOMAIN_USECASE):
        return f"Define a port interface in {source} and inject the adapter. Do not import directly from {target}."
    return f"{source} must not import from {target}. Pass dependencies via constructor injection instead."


class StructureValidator:
    """Walks ``src/`` and reports Clean Architecture import violations."""

    def validate(self, project_root: Path) -> ValidationReport:
        """Scan all ``.py`` files under ``src/`` and return a ``ValidationReport``.

        Args:
            project_root: Root of the scaffolded project (contains ``pyproject.toml``).

        Returns:
            A :class:`~scaffold_ca_python.models.violation.ValidationReport`.

        Raises:
            ScaffoldError: If ``src/`` does not exist under *project_root*.
        """
        src = project_root / "src"
        if not src.exists():
            raise ScaffoldError("Could not locate src/ under project root.")

        violations: list[Violation] = []
        files_scanned = 0

        for py_file in sorted(src.rglob("*.py")):
            classified = self._classify(py_file, src)
            if classified is None:
                continue
            python_package, source_layer = classified
            files_scanned += 1

            tree = self._parse(py_file)
            if tree is None:
                continue

            violations.extend(self._violations_in(tree, py_file, python_package, source_layer))

        return ValidationReport(
            project_root=project_root,
            files_scanned=files_scanned,
            violations=violations,
        )

    @staticmethod
    def _classify(py_file: Path, src: Path) -> tuple[str, Layer] | None:
        """Return (python_package, source_layer) if the file is in a known layer, else None."""
        try:
            rel = py_file.relative_to(src)
        except ValueError:
            return None
        parts = rel.parts
        if len(parts) < 2:
            return None
        python_package = parts[0]
        source_layer = _layer_from_path_parts(parts[1:])
        if source_layer is None:
            return None
        return python_package, source_layer

    @staticmethod
    def _parse(py_file: Path) -> ast.Module | None:
        """Parse *py_file* and return the AST, or None on SyntaxError (with a warning)."""
        try:
            content = py_file.read_text(encoding="utf-8")
            return ast.parse(content, filename=str(py_file))
        except SyntaxError:
            warnings.warn(f"could not parse '{py_file}' — skipping", stacklevel=2)
            return None

    @staticmethod
    def _violations_in(tree: ast.Module, py_file: Path, python_package: str, source_layer: Layer) -> list[Violation]:
        """Return all CA import violations found in *tree*."""
        forbidden = FORBIDDEN_IMPORTS.get(source_layer, [])
        violations: list[Violation] = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                target = _layer_from_module(node.module, python_package)
                if target is not None and target in forbidden:
                    names = ", ".join(a.name for a in node.names)
                    violations.append(
                        Violation(
                            source_file=py_file,
                            line_number=node.lineno,
                            import_statement=f"from {node.module} import {names}",
                            source_layer=source_layer,
                            target_layer=target,
                            resolution_hint=_make_hint(source_layer, target),
                        )
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    target = _layer_from_module(alias.name, python_package)
                    if target is not None and target in forbidden:
                        violations.append(
                            Violation(
                                source_file=py_file,
                                line_number=node.lineno,
                                import_statement=f"import {alias.name}",
                                source_layer=source_layer,
                                target_layer=target,
                                resolution_hint=_make_hint(source_layer, target),
                            )
                        )

        return violations
