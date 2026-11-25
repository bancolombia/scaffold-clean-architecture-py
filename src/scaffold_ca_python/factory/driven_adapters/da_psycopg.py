from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, override

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.dependencies import PSYCOPG_BINARY, PSYCOPG_POOL, PYDANTIC_SETTINGS
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

# Placeholder URL: the generated pool opens lazily, so no test ever connects to it.
_CONFTEST_FIXTURE = """\


@pytest.fixture(autouse=True)
def psycopg_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PSYCOPG_DATABASE_URL", "postgresql://user:password@localhost:5432/test")
"""

_CONFTEST_MARKER = "psycopg_env"


class DrivenAdapterPsycopg(DrivenAdapterFactory):
    """Factory for the psycopg 3 async driven-adapter type (raw SQL, no ORM)."""

    description: ClassVar[str] = "Async PostgreSQL with raw SQL (psycopg 3 pool)"
    fixed_name: ClassVar[str] = "psycopg"
    template_pkg: ClassVar[str] = "driven_adapter/psycopg"
    src_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("__init__.py", "__init__.py.jinja2"),
        ("psycopg_settings.py", "psycopg_settings.py.jinja2"),
        ("psycopg_config.py", "psycopg_config.py.jinja2"),
        ("psycopg_repository.py", "psycopg_repository.py.jinja2"),
    )
    test_files: ClassVar[tuple[tuple[str, str], ...]] = (("test_psycopg_adapter.py", "test_psycopg_adapter.py.jinja2"),)
    runtime_dependencies: ClassVar[tuple[str, ...]] = (PSYCOPG_BINARY, PSYCOPG_POOL, PYDANTIC_SETTINGS)

    @override
    def build_extra(self, builder: ModuleBuilder, ctx: dict[str, Any]) -> None:
        conftest_path = resolve_tests_root(builder.project_root) / "conftest.py"
        self.append_env_fixture(builder, conftest_path, _CONFTEST_MARKER, _CONFTEST_FIXTURE)
