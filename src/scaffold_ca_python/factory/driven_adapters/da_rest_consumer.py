"""DrivenAdapterRestConsumer factory implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory

if TYPE_CHECKING:
    from pathlib import Path

    from scaffold_ca_python.core.module_builder import ModuleBuilder

_CONFTEST_FIXTURE = """\


@pytest.fixture(autouse=True)
def rest_consumer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REST_CONSUMER_BASE_URL", "https://example.com")
"""

_CONFTEST_HEADER = '''\
"""Test fixtures for the generated project."""

from __future__ import annotations

import pytest
'''

_CONFTEST_MARKER = "rest_consumer_env"


def _append_rest_consumer_conftest(builder: ModuleBuilder, conftest_path: Path) -> None:
    """Append REST_CONSUMER_BASE_URL autouse fixture to conftest.py (idempotent)."""
    if builder.dry_run:
        return
    if conftest_path.exists():
        existing = conftest_path.read_text(encoding="utf-8")
        if _CONFTEST_MARKER in existing:
            return
        conftest_path.write_text(existing + _CONFTEST_FIXTURE, encoding="utf-8")
    else:
        conftest_path.parent.mkdir(parents=True, exist_ok=True)
        conftest_path.write_text(_CONFTEST_HEADER + _CONFTEST_FIXTURE, encoding="utf-8")


class DrivenAdapterRestConsumer(DrivenAdapterFactory):
    fixed_name = "rest_consumer"
    """Factory for REST Consumer driven-adapter type."""

    def build(self, builder: ModuleBuilder) -> None:
        """Build REST Consumer driven-adapter files and dependencies.

        Queues files:
        - src/infrastructure/driven_adapters/rest_consumer/__init__.py
        - src/infrastructure/driven_adapters/rest_consumer/rest_consumer.py
        - tests/infrastructure/driven_adapters/rest_consumer/test_rest_consumer.py

        Injects:
        - httpx~=0.28.1  (runtime dependency)
        - respx~=0.23.1  (test dependency-group)
        """
        project_root = builder.project_root
        pkg = builder.project_ctx.python_package

        # Setup directory paths
        src_dir = project_root / "src" / pkg / "infrastructure" / "driven_adapters" / "rest_consumer"
        test_dir = resolve_tests_root(project_root) / "infrastructure" / "driven_adapters" / "rest_consumer"

        # Template base path for driven_adapter/rest_consumer
        base = "driven_adapter/rest_consumer"

        # Build context dict from module context
        ctx_dict = {}
        if builder.module_ctx:
            ctx_dict.update(builder.module_ctx.model_dump())

        # Optional gateway for @wireup.injectable(as_type=...)
        ctx_dict["gateway"] = builder.get_param("gateway", default=None)

        # Add source files
        builder.add_file(
            src_dir / "__init__.py",
            builder.render(f"{base}/__init__.py.jinja2", ctx_dict),
            template_name=f"{base}/__init__.py.jinja2",
        )
        builder.add_file(
            src_dir / "rest_consumer_settings.py",
            builder.render(f"{base}/rest_consumer_settings.py.jinja2", ctx_dict),
            template_name=f"{base}/rest_consumer_settings.py.jinja2",
        )
        builder.add_file(
            src_dir / "rest_consumer.py",
            builder.render(f"{base}/rest_consumer.py.jinja2", ctx_dict),
            template_name=f"{base}/rest_consumer.py.jinja2",
        )

        self.append_wiring_test(builder, ctx_dict)

        # Add test files
        builder.add_file(
            test_dir / "test_rest_consumer.py",
            builder.render(f"{base}/test_rest_consumer.py.jinja2", ctx_dict),
            template_name=f"{base}/test_rest_consumer.py.jinja2",
            is_test=True,
        )

        # Append REST_CONSUMER_BASE_URL autouse fixture to src/tests/conftest.py (idempotent)
        conftest_path = resolve_tests_root(project_root) / "conftest.py"
        _append_rest_consumer_conftest(builder, conftest_path)

        # Add dependencies: httpx and pydantic-settings at runtime, respx only in test group
        builder.add_dependency("httpx~=0.28.1")
        builder.add_dependency("pydantic-settings~=2.15.0")
        builder.add_dependency("respx~=0.23.1", group="test")
