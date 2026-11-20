"""Migrate dependency-injector (0.5.0) projects to the wireup layout."""

from __future__ import annotations

import re
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.core.version import get_scaffold_version
from scaffold_ca_python.core.wiring_utils import (
    find_missing_adapters,
    is_gateway_module,
    replace_missing_adapters_marker,
)
from scaffold_ca_python.factory.upgrades.actions.di_wireup.project import (
    LEGACY_RESTAPI_APP,
    LEGACY_RESTAPI_TEST_APP,
    RESTAPI_APP,
    RESTAPI_TEST_APP,
    container_files,
    depends_on_dependency_injector,
    first_legacy_di_line,
    is_usecase_module,
    matches_legacy_render,
    migrated_pyproject,
    python_files,
    render_context,
    uses_legacy_di,
)
from scaffold_ca_python.factory.upgrades.base import UpgradeAction
from scaffold_ca_python.factory.upgrades.report import AppliedItem, PendingItem, UpgradeResult

if TYPE_CHECKING:
    from scaffold_ca_python.factory.upgrades.actions.di_wireup.codemod import Binding

_PROVIDER_REF = re.compile(r"^\w+(?:\.\w+)*\.(\w+)$")


class UpgradeDependencyInjectorToWireup(UpgradeAction):
    name = "dependency-injector-to-wireup"
    description = "Migrate from dependency-injector 4.x to wireup 2.13"

    @classmethod
    def applies(cls, builder: ModuleBuilder) -> bool:
        root = builder.project_root
        if depends_on_dependency_injector(root):
            return True
        return any(uses_legacy_di(p.read_text(encoding="utf-8")) for p in python_files(root / "src"))

    @classmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        from scaffold_ca_python.factory.upgrades.actions.di_wireup import codemod

        return _Migration(builder, codemod).run()


class _Migration:
    def __init__(self, builder: ModuleBuilder, codemod: ModuleType) -> None:
        self.builder = builder
        self.codemod = codemod
        self.root = builder.project_root
        self.pkg = builder.project_ctx.python_package
        self.src_pkg = self.root / "src" / self.pkg
        self.config_dir = self.src_pkg / "application" / "config"
        self.tests_root = resolve_tests_root(self.root)
        self.result = UpgradeResult()
        self.gateways_needed: set[str] = set()
        self.gateways_implemented: set[str] = set()
        self.app_replaced = False

    def rel(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def applied(self, kind: str, path: Path, description: str = "") -> None:
        self.result.applied.append(AppliedItem(kind=kind, file=self.rel(path), description=description))

    def pending(self, kind: str, path: Path, line: int) -> None:
        item = PendingItem(kind=kind, file=self.rel(path), line=line)
        if item not in self.result.pending:
            self.result.pending.append(item)

    def module_path(self, module: str) -> Path:
        return self.root / "src" / Path(*module.split(".")).with_suffix(".py")

    def run(self) -> UpgradeResult:
        self.migrate_pyproject()
        self.ensure_wiring()
        containers = container_files(self.src_pkg)
        self.migrate_containers(containers)
        self.migrate_modules(set(containers))
        self.replace_bootstrap_test()
        self.report_test_overrides()
        self.ensure_wiring_test()
        return self.result

    def migrate_pyproject(self) -> None:
        content = migrated_pyproject(self.root, get_scaffold_version())
        if content is not None:
            path = self.root / "pyproject.toml"
            self.builder.add_file(path, content, overwrite=True)
            self.applied("pyproject_update", path, "dependency-injector → wireup, tooling keys, scaffold_version")

    def ensure_wiring(self) -> None:
        wiring = self.config_dir / "wiring.py"
        if not wiring.exists():
            template = "project/application/config/wiring.py.jinja2"
            self.builder.add_rendered(wiring, template, self.builder.base_context())
            self.applied("wiring_created", wiring, "wireup container with package-scan INJECTABLES")
        usecases_init = self.config_dir / "usecases" / "__init__.py"
        if not usecases_init.exists():
            self.builder.add_rendered(
                usecases_init,
                "project/application/config/usecases/__init__.py.jinja2",
                self.builder.base_context(),
            )

    def migrate_containers(self, containers: list[Path]) -> None:
        analysis = self.codemod.analyze_containers(containers)
        blocked: set[Path] = set()
        for finding in analysis.findings:
            self.pending(finding.kind, finding.file, finding.line)
            blocked.add(finding.file)

        by_name = {b.name: b for b in analysis.bindings}
        as_type_hints: dict[tuple[str, str], tuple[str, str]] = {}
        components: list[Binding] = []
        for binding in analysis.bindings:
            module = binding.module or ""
            if module.startswith(f"{self.pkg}.") and is_usecase_module(module):
                if not self.migrate_usecase(binding, by_name, as_type_hints):
                    blocked.add(binding.file)
            elif module.startswith(f"{self.pkg}.") and ".infrastructure." in module:
                components.append(binding)
            else:
                self.pending("callable_provider", binding.file, binding.line)
                blocked.add(binding.file)

        blocked |= self.decorate_components(components, as_type_hints)
        for container in containers:
            if container not in blocked:
                self.builder.delete_file(container)
                self.applied("container_removed", container, "declarative container replaced by package scan")

    def decorate_components(
        self,
        components: list[Binding],
        as_type_hints: dict[tuple[str, str], tuple[str, str]],
    ) -> set[Path]:
        """Queue ``@wireup.injectable`` on adapters/helpers; return containers left with pending items."""
        blocked: set[Path] = set()
        edits: dict[Path, list[tuple[str, tuple[str, str] | None, str]]] = {}
        for binding in components:
            assert binding.module is not None
            path = self.module_path(binding.module)
            params = self.codemod.class_init_params(path, binding.class_name)
            if binding.kwargs or params is None or any(p.annotation is None and not p.has_default for p in params):
                self.pending("provider_arguments", binding.file, binding.line)
                blocked.add(binding.file)
                continue
            as_type = self.codemod.class_gateway_base(path, binding.class_name) or as_type_hints.get(
                (binding.module, binding.class_name)
            )
            if as_type is not None:
                self.gateways_implemented.add(as_type[1])
            edits.setdefault(path, []).append((binding.class_name, as_type, binding.lifetime))

        for path, classes in edits.items():
            source = path.read_text(encoding="utf-8")
            decorated: list[str] = []
            for class_name, as_type, lifetime in classes:
                updated = self.codemod.add_injectable(source, class_name, as_type=as_type, lifetime=lifetime)
                if updated is not None:
                    source = updated
                    decorated.append(class_name)
            if decorated:
                self.builder.add_file(path, source, overwrite=True)
                self.applied("injectable_on_adapter", path, f"@wireup.injectable on {', '.join(decorated)}")
        return blocked

    def migrate_usecase(
        self,
        b: Binding,
        by_name: dict[str, Binding],
        as_type_hints: dict[tuple[str, str], tuple[str, str]],
    ) -> bool:
        assert b.module is not None
        params = self.codemod.class_init_params(self.module_path(b.module), b.class_name)
        if params is None:
            self.pending("provider_arguments", b.file, b.line)
            return False
        by_param = {p.name: p for p in params}
        ok = True
        for kw, value in b.kwargs.items():
            param = by_param.get(kw)
            match = _PROVIDER_REF.match(value)
            target = by_name.get(match.group(1)) if match else None
            if param is None or target is None or target.module is None or param.annotation is None:
                ok = False
                continue
            gateway = param.imports[0] if len(param.imports) == 1 else None
            if gateway is not None and gateway[1] == param.annotation and is_gateway_module(gateway[0]):
                as_type_hints[(target.module, target.class_name)] = gateway
        selected = [p for p in params if p.name in b.kwargs or not p.has_default]
        if not ok or any(p.annotation is None for p in selected):
            self.pending("provider_arguments", b.file, b.line)
            return False
        for p in selected:
            if any(".infrastructure.helpers." in mod for mod, _ in p.imports):
                self.pending("usecase_uses_helper", b.file, b.line)
            self.gateways_needed.update(name for mod, name in p.imports if is_gateway_module(mod))
        factory = self.config_dir / "usecases" / f"{b.module.rsplit('.', 1)[-1]}.py"
        if not factory.exists():
            content = self.codemod.render_factory(
                usecase_module=b.module,
                class_name=b.class_name,
                params=selected,
                lifetime=b.lifetime,
            )
            self.builder.add_file(factory, content)
            self.applied("container_to_factory", factory, f"from providers binding {b.name}")
        return True

    def migrate_modules(self, containers: set[Path]) -> None:
        container_module = f"{self.pkg}.application.config.container"
        roots = {self.src_pkg, self.src_pkg / "application"}
        for path in python_files(self.src_pkg):
            if path in containers or path.is_relative_to(self.config_dir / "usecases"):
                continue
            text = path.read_text(encoding="utf-8")
            if not uses_legacy_di(text):
                continue
            if path.parent in roots:
                app = self.src_pkg / "application" / "app.py"
                if path == app and matches_legacy_render(self.builder, path, LEGACY_RESTAPI_APP):
                    self.builder.add_rendered(path, RESTAPI_APP, render_context(self.builder), overwrite=True)
                    self.applied("composition_root_replaced", path, "0.5.0 restapi app.py → wireup FastAPI setup")
                    self.app_replaced = True
                else:
                    self.pending("composition_root_modified", path, first_legacy_di_line(text))
                continue
            rewrite = self.codemod.rewrite_injections(text, container_module)
            if rewrite.source != text:
                self.builder.add_file(path, rewrite.source, overwrite=True)
                self.applied("provide_to_injected", path, f"{rewrite.converted} parameter(s) → Injected[...]")
            for line in rewrite.unresolved:
                self.pending("injection_unresolved", path, line)
            if not rewrite.unresolved and uses_legacy_di(rewrite.source):
                self.pending("injection_unresolved", path, first_legacy_di_line(rewrite.source))

    def replace_bootstrap_test(self) -> None:
        """Swap the 0.5.0 restapi ``test_app.py`` once its ``app.py`` is (or is being) migrated."""
        app = self.src_pkg / "application" / "app.py"
        app_migrated = self.app_replaced or (app.is_file() and not uses_legacy_di(app.read_text(encoding="utf-8")))
        path = self.tests_root / "application" / "test_app.py"
        if app_migrated and matches_legacy_render(self.builder, path, LEGACY_RESTAPI_TEST_APP):
            self.builder.add_rendered(path, RESTAPI_TEST_APP, render_context(self.builder), overwrite=True)
            self.applied("composition_root_replaced", path, "0.5.0 restapi test_app.py → 1.0.0 template")

    def report_test_overrides(self) -> None:
        for path in python_files(self.tests_root):
            text = path.read_text(encoding="utf-8")
            lines = set(self.codemod.override_lines(text)) if ".override" in text or ".container" in text else set()
            if uses_legacy_di(text):
                lines.add(first_legacy_di_line(text))
            for line in sorted(lines):
                self.pending("override_in_test", path, line)

    def ensure_wiring_test(self) -> None:
        path = self.tests_root / "application" / "config" / "test_wiring.py"
        if path.exists():
            return
        content = self.builder.render("project/test_wiring.py.jinja2", self.builder.base_context())
        missing = (set(find_missing_adapters(self.src_pkg)) | self.gateways_needed) - self.gateways_implemented
        content = replace_missing_adapters_marker(content, sorted(missing)) or content
        self.builder.add_file(path, content)
        self.applied("wiring_test_created", path, "container smoke test (validates the wireup graph)")
