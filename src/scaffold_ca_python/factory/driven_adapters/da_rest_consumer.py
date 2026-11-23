from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.dependencies import HTTPX, PYDANTIC_SETTINGS, RESPX
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

_CONFTEST_FIXTURE = """\


@pytest.fixture(autouse=True)
def rest_consumer_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REST_CONSUMER_BASE_URL", "https://example.com")
"""

_CONFTEST_MARKER = "rest_consumer_env"


class DrivenAdapterRestConsumer(DrivenAdapterFactory):
    """Factory for REST Consumer driven-adapter type."""

    description: ClassVar[str] = "HTTP outbound client (httpx)"
    fixed_name: ClassVar[str] = "rest_consumer"
    template_pkg: ClassVar[str] = "driven_adapter/rest_consumer"
    src_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("__init__.py", "__init__.py.jinja2"),
        ("rest_consumer_settings.py", "rest_consumer_settings.py.jinja2"),
        ("rest_consumer_config.py", "rest_consumer_config.py.jinja2"),
        ("rest_consumer.py", "rest_consumer.py.jinja2"),
    )
    test_files: ClassVar[tuple[tuple[str, str], ...]] = (("test_rest_consumer.py", "test_rest_consumer.py.jinja2"),)
    runtime_dependencies: ClassVar[tuple[str, ...]] = (HTTPX, PYDANTIC_SETTINGS)
    test_group_dependencies: ClassVar[tuple[str, ...]] = (RESPX,)

    def build_extra(self, builder: ModuleBuilder, ctx: dict[str, object]) -> None:
        del ctx
        conftest_path = resolve_tests_root(builder.project_root) / "conftest.py"
        self.append_env_fixture(builder, conftest_path, _CONFTEST_MARKER, _CONFTEST_FIXTURE)
