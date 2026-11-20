"""Migrate dependency-injector projects to wireup."""

from __future__ import annotations

from pathlib import Path

from scaffold_ca_python.core.adapter_injectable import injectable_transform
from scaffold_ca_python.core.composition_fingerprints import COMPOSITION_CANDIDATES, composition_root_status
from scaffold_ca_python.core.di_container_codemod import extract_singleton_usecases, render_minimal_usecase_factory
from scaffold_ca_python.core.legacy_di_migration import (
    find_container_files,
    migrate_pyproject_to_wireup,
    pyproject_has_package,
    rewrite_provide_to_injected,
    scan_container_pending,
)
from scaffold_ca_python.core.module_builder import ModuleBuilder
from scaffold_ca_python.core.version import get_scaffold_version
from scaffold_ca_python.factory.upgrades.base import UpgradeAction
from scaffold_ca_python.factory.upgrades.report import AppliedItem, PendingItem, UpgradeResult


def _iter_python_files(base: Path) -> list[Path]:
    if not base.is_dir():
        return []
    return sorted(p for p in base.rglob("*.py") if p.is_file())


def _ensure_wireup_config(
    builder: ModuleBuilder,
    root: Path,
    config_dir: Path,
    applied: list[AppliedItem],
) -> None:
    wiring_path = config_dir / "wiring.py"
    usecases_init = config_dir / "usecases" / "__init__.py"
    if not wiring_path.exists():
        builder.add_rendered(
            wiring_path,
            "project/application/config/wiring.py.jinja2",
            builder.project_ctx,
            overwrite=False,
        )
        applied.append(
            AppliedItem(
                kind="wiring_created",
                file=str(wiring_path.relative_to(root)),
                description="wireup wiring.py generated",
            )
        )
    if not usecases_init.exists():
        builder.add_rendered(
            usecases_init,
            "project/application/config/usecases/__init__.py.jinja2",
            builder.project_ctx,
            overwrite=False,
        )


def _composition_pending(root: Path, src_pkg: Path, pending: list[PendingItem]) -> None:
    for rel_name in COMPOSITION_CANDIDATES:
        candidate = src_pkg / rel_name
        if composition_root_status(candidate) == "modified":
            pending.append(
                PendingItem(
                    kind="composition_root_modified",
                    file=str(candidate.relative_to(root)),
                    line=1,
                    guide_section="composition-root",
                )
            )


def _migrate_container(
    container: Path,
    root: Path,
    pkg: str,
    builder: ModuleBuilder,
    config_dir: Path,
    applied: list[AppliedItem],
    pending: list[PendingItem],
) -> None:
    rel = str(container.relative_to(root))
    source = container.read_text(encoding="utf-8")
    singletons, libcst_pending = extract_singleton_usecases(source, python_package=pkg)
    guide_map = {
        "resource_provider": "providers-resource",
        "configuration_provider": "providers-configuration",
        "selector_provider": "providers-selector",
        "factory_provider": "providers-factory",
    }
    for line, kind in libcst_pending:
        pending.append(PendingItem(kind=kind, file=rel, line=line, guide_section=guide_map.get(kind, kind)))
    for kind, line, section in scan_container_pending(container):
        if not any(p.file == rel and p.line == line for p in pending):
            pending.append(PendingItem(kind=kind, file=rel, line=line, guide_section=section))
    usecases_dir = config_dir / "usecases"
    for binding in singletons:
        factory_path = usecases_dir / f"{binding.usecase_module}.py"
        content = render_minimal_usecase_factory(
            python_package=pkg,
            module_name=binding.usecase_module,
            class_name=binding.class_name,
        )
        builder.add_file(factory_path, content, overwrite=False)
        applied.append(
            AppliedItem(
                kind="container_to_factory",
                file=str(factory_path.relative_to(root)),
                description=f"from providers.Singleton({binding.class_name})",
            )
        )
    builder.delete_file(container)
    applied.append(AppliedItem(kind="container_removed", file=rel, description="legacy declarative container removed"))


class UpgradeDependencyInjectorToWireup(UpgradeAction):
    name = "dependency-injector-to-wireup"
    description = "Migrate from dependency-injector 4.x to wireup 2.13"

    @classmethod
    def applies(cls, builder: ModuleBuilder) -> bool:
        root = builder.project_root
        pkg = builder.project_ctx.python_package
        if pyproject_has_package(root, "dependency-injector"):
            return True
        if find_container_files(root, pkg):
            return True
        wiring = root / "src" / pkg / "application" / "config" / "wiring.py"
        return wiring.is_file() and "dependency_injector" in wiring.read_text(encoding="utf-8")

    @classmethod
    def up(cls, builder: ModuleBuilder) -> UpgradeResult:
        applied: list[AppliedItem] = []
        pending: list[PendingItem] = []
        root = builder.project_root
        pkg = builder.project_ctx.python_package
        src_pkg = root / "src" / pkg

        if migrate_pyproject_to_wireup(root, get_scaffold_version(), dry_run=builder.dry_run):
            applied.append(
                AppliedItem(
                    kind="pyproject_update",
                    file="pyproject.toml",
                    description="wireup dependency and scaffold_version key written",
                )
            )

        config_dir = src_pkg / "application" / "config"
        _ensure_wireup_config(builder, root, config_dir, applied)
        _composition_pending(root, src_pkg, pending)
        for container in find_container_files(root, pkg):
            _migrate_container(container, root, pkg, builder, config_dir, applied, pending)

        da_root = src_pkg / "infrastructure" / "driven_adapters"
        for path in _iter_python_files(da_root):
            original = path.read_text(encoding="utf-8")
            updated, changed = injectable_transform(original)
            if changed:
                builder.add_file(path, updated, overwrite=True)
                applied.append(
                    AppliedItem(
                        kind="injectable_on_adapter",
                        file=str(path.relative_to(root)),
                        description="@injectable added",
                    )
                )

        ep_root = src_pkg / "infrastructure" / "entry_points"
        for path in _iter_python_files(ep_root):
            text = path.read_text(encoding="utf-8")
            if "Provide[" not in text:
                continue
            updated, n = rewrite_provide_to_injected(text)
            if n:
                builder.add_file(path, updated, overwrite=True)
                rel = str(path.relative_to(root))
                applied.append(
                    AppliedItem(
                        kind="provide_to_injected",
                        file=rel,
                        description=f"Provide → Injected on {n} occurrence(s)",
                    )
                )

        return UpgradeResult(applied=applied, pending=pending)
