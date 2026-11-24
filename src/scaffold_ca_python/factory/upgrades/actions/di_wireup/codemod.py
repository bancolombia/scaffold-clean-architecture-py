"""libcst transforms for the dependency-injector → wireup action (imported lazily)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import override

import libcst as cst
from libcst import matchers as m
from libcst.codemod import CodemodContext
from libcst.codemod.visitors import AddImportsVisitor, RemoveImportsVisitor
from libcst.metadata import MetadataWrapper, PositionProvider

from scaffold_ca_python.core.wiring_utils import is_gateway_module

_BINDING_PROVIDERS = {"Singleton": "singleton", "ThreadSafeSingleton": "singleton", "Factory": "transient"}
_STRUCTURAL_PROVIDERS = {"Container", "DependenciesContainer"}
_PENDING_PROVIDERS = {
    "Resource": "resource_provider",
    "Configuration": "configuration_provider",
    "Selector": "selector_provider",
}


@dataclass(frozen=True, slots=True)
class Binding:
    """A ``providers.Singleton/Factory(Cls, **kwargs)`` declaration in a container."""

    name: str
    class_name: str
    module: str | None
    lifetime: str
    kwargs: dict[str, str]
    file: Path
    line: int


@dataclass(frozen=True, slots=True)
class Finding:
    kind: str
    file: Path
    line: int


@dataclass
class ContainerAnalysis:
    bindings: list[Binding] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class InitParam:
    name: str
    annotation: str | None
    imports: tuple[tuple[str, str], ...]
    has_default: bool


def import_map(module: cst.Module) -> dict[str, str]:
    """Map local names to the absolute module they are imported from (``from X import Y``)."""
    names: dict[str, str] = {}
    for stmt in module.body:
        if not isinstance(stmt, cst.SimpleStatementLine):
            continue
        for small in stmt.body:
            if not isinstance(small, cst.ImportFrom) or small.relative or small.module is None:
                continue
            if isinstance(small.names, cst.ImportStar):
                continue
            mod = cst.Module([]).code_for_node(small.module)
            for alias in small.names:
                local = alias.asname.name if alias.asname else alias.name
                if isinstance(local, cst.Name):
                    names[local.value] = mod
    return names


def _provider_attr(value: cst.BaseExpression) -> tuple[str, cst.Call] | None:
    if m.matches(value, m.Call(func=m.Attribute(value=m.Name("providers")))):
        assert isinstance(value, cst.Call)
        assert isinstance(value.func, cst.Attribute)
        return value.func.attr.value, value
    return None


def _is_declarative_container(node: cst.ClassDef) -> bool:
    return any(
        m.matches(base.value, m.Attribute(attr=m.Name("DeclarativeContainer")) | m.Name("DeclarativeContainer"))
        for base in node.bases
    )


class _ContainerVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, path: Path, imports: dict[str, str], known_containers: set[str]) -> None:
        self.path = path
        self.imports = imports
        self.known_containers = known_containers
        self.result = ContainerAnalysis()
        self._depth = 0

    def _line(self, node: cst.CSTNode) -> int:
        return self.get_metadata(PositionProvider, node).start.line

    def visit_ClassDef(self, node: cst.ClassDef) -> bool:
        if not _is_declarative_container(node):
            return False
        if self._depth > 0:
            self.result.findings.append(Finding("nested_container", self.path, self._line(node)))
            return False
        self._depth += 1
        return True

    def leave_ClassDef(self, original_node: cst.ClassDef) -> None:
        if _is_declarative_container(original_node) and self._depth > 0:
            self._depth -= 1

    def visit_Assign(self, node: cst.Assign) -> None:
        if self._depth and len(node.targets) == 1 and isinstance(node.targets[0].target, cst.Name):
            self._provider(node.targets[0].target.value, node.value, node)

    def visit_AnnAssign(self, node: cst.AnnAssign) -> None:
        if self._depth and node.value is not None and isinstance(node.target, cst.Name):
            self._provider(node.target.value, node.value, node)

    def _provider(self, name: str, value: cst.BaseExpression, node: cst.CSTNode) -> None:
        found = _provider_attr(value)
        if found is None:
            return
        provider, call = found
        line = self._line(node)
        if provider in _STRUCTURAL_PROVIDERS:
            first = call.args[0].value if call.args else None
            if provider == "Container" and not (isinstance(first, cst.Name) and first.value in self.known_containers):
                self.result.findings.append(Finding("nested_container", self.path, line))
            return
        if provider in _PENDING_PROVIDERS:
            self.result.findings.append(Finding(_PENDING_PROVIDERS[provider], self.path, line))
            return
        if provider not in _BINDING_PROVIDERS:
            self.result.findings.append(Finding("callable_provider", self.path, line))
            return
        positional = [a for a in call.args if a.keyword is None]
        if not positional or not isinstance(positional[0].value, cst.Name) or len(positional) > 1:
            self.result.findings.append(Finding("provider_arguments", self.path, line))
            return
        class_name = positional[0].value.value
        kwargs = {a.keyword.value: cst.Module([]).code_for_node(a.value) for a in call.args if a.keyword is not None}
        self.result.bindings.append(
            Binding(
                name=name,
                class_name=class_name,
                module=self.imports.get(class_name),
                lifetime=_BINDING_PROVIDERS[provider],
                kwargs=kwargs,
                file=self.path,
                line=line,
            )
        )


def _parse(path: Path) -> cst.Module | None:
    try:
        return cst.parse_module(path.read_text(encoding="utf-8"))
    except cst.ParserSyntaxError:
        return None


def analyze_containers(files: Sequence[Path]) -> ContainerAnalysis:
    """Collect provider bindings and unsupported providers from declarative containers."""
    parsed: dict[Path, cst.Module] = {}
    analysis = ContainerAnalysis()
    known: set[str] = set()
    for path in files:
        module = _parse(path)
        if module is None:
            analysis.findings.append(Finding("injection_unresolved", path, 1))
            continue
        parsed[path] = module
        known.update(n.name.value for n in module.body if isinstance(n, cst.ClassDef) and _is_declarative_container(n))
    for path, module in parsed.items():
        visitor = _ContainerVisitor(path, import_map(module), known)
        MetadataWrapper(module).visit(visitor)
        analysis.bindings.extend(visitor.result.bindings)
        analysis.findings.extend(visitor.result.findings)
    return analysis


def _names_in(node: cst.CSTNode) -> set[str]:
    found: set[str] = set()

    class _Collector(cst.CSTVisitor):
        def visit_Name(self, name: cst.Name) -> None:
            found.add(name.value)

    node.visit(_Collector())
    return found


def _find_class(module: cst.Module, class_name: str) -> cst.ClassDef | None:
    return next(
        (n for n in module.body if isinstance(n, cst.ClassDef) and n.name.value == class_name),
        None,
    )


def class_init_params(path: Path, class_name: str) -> list[InitParam] | None:
    """Return ``__init__`` parameters (without ``self``) or None when the class is not found."""
    module = _parse(path)
    if module is None:
        return None
    cls = _find_class(module, class_name)
    if cls is None:
        return None
    imports = import_map(module)
    init = next(
        (n for n in cls.body.body if isinstance(n, cst.FunctionDef) and n.name.value == "__init__"),
        None,
    )
    if init is None:
        return []
    params: list[InitParam] = []
    for param in [*init.params.params[1:], *init.params.kwonly_params]:
        annotation = param.annotation.annotation if param.annotation else None
        needed = tuple(
            sorted((imports[n], n) for n in (_names_in(annotation) if annotation else set()) if n in imports)
        )
        params.append(
            InitParam(
                name=param.name.value,
                annotation=module.code_for_node(annotation) if annotation else None,
                imports=needed,
                has_default=param.default is not None,
            )
        )
    return params


def class_gateway_base(path: Path, class_name: str) -> tuple[str, str] | None:
    """Return ``(module, name)`` of the first base class imported from a gateway module."""
    module = _parse(path)
    cls = _find_class(module, class_name) if module else None
    if module is None or cls is None:
        return None
    imports = import_map(module)
    for base in cls.bases:
        if isinstance(base.value, cst.Name) and is_gateway_module(imports.get(base.value.value, "")):
            return imports[base.value.value], base.value.value
    return None


def render_factory(
    *,
    usecase_module: str,
    class_name: str,
    params: Sequence[InitParam],
    lifetime: str,
) -> str:
    """Render an ``application/config/usecases`` factory module for a use case."""
    stem = usecase_module.rsplit(".", 1)[-1]
    imports = sorted({imp for p in params for imp in p.imports})
    import_lines = "".join(f"from {mod} import {name}\n" for mod, name in imports)
    decorator = "@wireup.injectable" if lifetime == "singleton" else f'@wireup.injectable(lifetime="{lifetime}")'
    signature = "".join(f"    {p.name}: {p.annotation},\n" for p in params)
    call_args = "".join(f"        {p.name}={p.name},\n" for p in params)
    body = f"    return {class_name}(\n{call_args}    )\n" if params else f"    return {class_name}()\n"
    return (
        f'"""Factory for {class_name} — migrated from the dependency-injector container."""\n\n'
        "from __future__ import annotations\n\n"
        "import wireup\n\n"
        f"{import_lines}from {usecase_module} import {class_name}\n\n\n"
        f"{decorator}\n"
        f"def {stem}_factory(\n{signature}) -> {class_name}:\n"
        f'    """Construct {class_name} with its dependencies."""\n'
        f"{body}"
    )


def _is_injectable_decorator(dec: cst.Decorator) -> bool:
    target = dec.decorator.func if isinstance(dec.decorator, cst.Call) else dec.decorator
    return m.matches(target, m.Name("injectable") | m.Attribute(attr=m.Name("injectable")))


class _AddDecorator(cst.CSTTransformer):
    def __init__(self, class_name: str, decorator: str) -> None:
        self.class_name = class_name
        self.decorator = decorator
        self.changed = False

    @override
    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        if updated_node.name.value != self.class_name or any(
            _is_injectable_decorator(d) for d in updated_node.decorators
        ):
            return updated_node
        self.changed = True
        new = cst.Decorator(decorator=cst.parse_expression(self.decorator))
        return updated_node.with_changes(decorators=[new, *updated_node.decorators])


def add_injectable(
    source: str,
    class_name: str,
    *,
    as_type: tuple[str, str] | None,
    lifetime: str,
) -> str | None:
    """Return *source* with ``@wireup.injectable`` on *class_name*, or None when unchanged."""
    module = cst.parse_module(source)
    args: list[str] = []
    if as_type is not None:
        args.append(f"as_type={as_type[1]}")
    if lifetime != "singleton":
        args.append(f'lifetime="{lifetime}"')
    decorator = f"wireup.injectable({', '.join(args)})" if args else "wireup.injectable"
    transformer = _AddDecorator(class_name, decorator)
    module = module.visit(transformer)
    if not transformer.changed:
        return None
    context = CodemodContext()
    AddImportsVisitor.add_needed_import(context, "wireup")
    if as_type is not None and as_type[1] not in import_map(module):
        AddImportsVisitor.add_needed_import(context, as_type[0], as_type[1])
    return AddImportsVisitor(context).transform_module(module).code


_PROVIDE = m.Subscript(value=m.Name("Provide"))
_DEPENDS_PROVIDE = m.Call(func=m.Name("Depends"), args=[m.Arg(value=_PROVIDE)])


def _is_provide_param(param: cst.Param) -> bool:
    return param.default is not None and m.matches(param.default, _PROVIDE | _DEPENDS_PROVIDE)


class _InjectionTransformer(cst.CSTTransformer):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.converted = 0
        self.unresolved: list[int] = []
        self._convertible: set[int] = set()

    def visit_Parameters(self, node: cst.Parameters) -> None:
        """Mark Provide parameters whose default can be dropped without breaking default ordering."""
        seen_default = any(p.default is not None for p in node.posonly_params)
        for param in node.params:
            if _is_provide_param(param) and param.annotation is not None and not seen_default:
                self._convertible.add(id(param))
            elif param.default is not None:
                seen_default = True
        self._convertible.update(id(p) for p in node.kwonly_params if _is_provide_param(p) and p.annotation)

    def leave_Param(self, original_node: cst.Param, updated_node: cst.Param) -> cst.Param:
        if not _is_provide_param(original_node):
            return updated_node
        if id(original_node) not in self._convertible or updated_node.annotation is None:
            self.unresolved.append(self.get_metadata(PositionProvider, original_node).start.line)
            return updated_node
        self.converted += 1
        injected = cst.Subscript(
            value=cst.Name("Injected"),
            slice=[cst.SubscriptElement(slice=cst.Index(value=updated_node.annotation.annotation))],
        )
        return updated_node.with_changes(
            annotation=cst.Annotation(annotation=injected),
            default=None,
            equal=cst.MaybeSentinel.DEFAULT,
        )

    @override
    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        kept = [
            d
            for d in updated_node.decorators
            if not m.matches(d.decorator, m.Name("inject") | m.Attribute(value=m.Name("wiring"), attr=m.Name("inject")))
        ]
        return updated_node.with_changes(decorators=kept)


@dataclass(frozen=True, slots=True)
class InjectionRewrite:
    source: str
    converted: int
    unresolved: list[int]


def rewrite_injections(source: str, container_module: str) -> InjectionRewrite:
    """Turn ``Provide[...]`` / ``Depends(Provide[...])`` parameters into ``Injected[T]`` and drop ``@inject``."""
    module = cst.parse_module(source)
    transformer = _InjectionTransformer()
    module = MetadataWrapper(module).visit(transformer)
    context = CodemodContext()
    for mod, name in (
        ("dependency_injector.wiring", "Provide"),
        ("dependency_injector.wiring", "inject"),
        (container_module, "Container"),
    ):
        RemoveImportsVisitor.remove_unused_import(context, mod, name)
    if transformer.converted:
        RemoveImportsVisitor.remove_unused_import(context, "fastapi", "Depends")
    module = RemoveImportsVisitor(context).transform_module(module)
    if transformer.converted:
        add_context = CodemodContext()
        AddImportsVisitor.add_needed_import(add_context, "wireup", "Injected")
        module = AddImportsVisitor(add_context).transform_module(module)
    return InjectionRewrite(module.code, transformer.converted, transformer.unresolved)


class _OverrideVisitor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self) -> None:
        self.lines: list[int] = []

    def visit_Call(self, node: cst.Call) -> None:
        if m.matches(node.func, m.Attribute(attr=m.Name("override") | m.Name("override_providers"))):
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)

    def visit_Attribute(self, node: cst.Attribute) -> None:
        if m.matches(node, m.Attribute(value=m.Attribute(attr=m.Name("state")), attr=m.Name("container"))):
            self.lines.append(self.get_metadata(PositionProvider, node).start.line)


def override_lines(source: str) -> list[int]:
    """Return lines that override container providers or reach ``app.state.container`` (code only)."""
    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError:
        return [1]
    visitor = _OverrideVisitor()
    MetadataWrapper(module).visit(visitor)
    return sorted(set(visitor.lines))
