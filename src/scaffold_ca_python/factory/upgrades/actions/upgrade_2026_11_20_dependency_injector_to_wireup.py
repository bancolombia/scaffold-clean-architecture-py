"""Migrate dependency-injector projects to wireup."""

from __future__ import annotations

from pathlib import Path

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

        for container in find_container_files(root, pkg):
            rel = str(container.relative_to(root))
            for kind, line, section in scan_container_pending(container):
                pending.append(PendingItem(kind=kind, file=rel, line=line, guide_section=section))
            builder.delete_file(container)
            applied.append(
                AppliedItem(kind="container_removed", file=rel, description="legacy declarative container removed")
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
