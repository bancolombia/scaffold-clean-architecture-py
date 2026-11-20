"""libcst helpers to extract use-case wiring from declarative containers."""

from __future__ import annotations

from dataclasses import dataclass

import libcst as cst
from libcst import matchers as m
from libcst.metadata import MetadataWrapper, PositionProvider


@dataclass(frozen=True, slots=True)
class SingletonBinding:
    class_name: str
    line: int
    usecase_module: str


def extract_singleton_usecases(
    source: str, *, python_package: str
) -> tuple[list[SingletonBinding], list[tuple[int, str]]]:
    """Return Singleton bindings and (line, provider_kind) pairs for non-mapped providers."""
    try:
        module = cst.parse_module(source)
    except Exception:
        return [], [(1, "callable_provider")]

    bindings: list[SingletonBinding] = []
    pending: list[tuple[int, str]] = []
    wrapper = MetadataWrapper(module)
    visitor = _SingletonVisitor(python_package=python_package)
    wrapper.visit(visitor)
    bindings.extend(visitor.bindings)
    pending.extend(visitor.pending)
    return bindings, pending


class _SingletonVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, *, python_package: str) -> None:
        self.python_package = python_package
        self.bindings: list[SingletonBinding] = []
        self.pending: list[tuple[int, str]] = []

    def visit_Assign(self, node: cst.Assign) -> None:
        if len(node.targets) != 1:
            return
        value = node.value
        if m.matches(value, m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Singleton")))):
            assert isinstance(value, cst.Call)
            class_name = _first_arg_name(value)
            line = self.get_metadata(PositionProvider, node).start.line
            if class_name:
                snake = _pascal_to_snake_usecase(class_name)
                self.bindings.append(
                    SingletonBinding(
                        class_name=class_name,
                        line=line,
                        usecase_module=f"{snake}_usecase",
                    )
                )
            return
        for kind, matcher in _PENDING_MATCHERS.items():
            if m.matches(value, matcher):
                line = self.get_metadata(PositionProvider, node).start.line
                self.pending.append((line, kind))
                return

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if node.value is None:
            return
        value = node.value
        if m.matches(value, m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Resource")))):
            line = self.get_metadata(PositionProvider, node).start.line
            self.pending.append((line, "resource_provider"))


_PENDING_MATCHERS = {
    "resource_provider": m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Resource"))),
    "configuration_provider": m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Configuration"))),
    "selector_provider": m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Selector"))),
    "factory_provider": m.Call(func=m.Attribute(value=m.Name("providers"), attr=m.Name("Factory"))),
}


def _first_arg_name(call: cst.Call) -> str | None:
    if not call.args:
        return None
    arg = call.args[0].value
    if isinstance(arg, cst.Name):
        return arg.value
    return None


def _pascal_to_snake_usecase(class_name: str) -> str:
    base = class_name[: -len("UseCase")] if class_name.endswith("UseCase") else class_name
    return "".join(f"_{c.lower()}" if c.isupper() else c for c in base).lstrip("_")


def render_minimal_usecase_factory(
    *,
    python_package: str,
    module_name: str,
    class_name: str,
    gateway_params: list[tuple[str, str]] | None = None,
) -> str:
    """Render a minimal factory when gateways cannot be inferred (stubs for manual edit)."""
    gateway_params = gateway_params or []
    params = ",\n    ".join(f"{name}: {typ}" for name, typ in gateway_params)
    args = ",\n        ".join(f"{name}={name}" for name, _ in gateway_params)
    header = f'"""Factory for {class_name} — generated from legacy container (review gateways)."""\n\n'
    header += "from __future__ import annotations\n\nimport wireup\n\n"
    header += f"from {python_package}.domain.usecase.{module_name} import {class_name}\n\n\n"
    header += "@wireup.injectable\n"
    header += f"def {module_name}_factory(\n"
    if params:
        header += f"    {params},\n"
    header += f") -> {class_name}:\n"
    header += f'    """Construct {class_name}."""\n'
    if gateway_params:
        header += f"    return {class_name}(\n        {args},\n    )\n"
    else:
        header += f"    return {class_name}()\n"
    return header
