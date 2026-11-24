from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from scaffold_ca_python.core.project_detector import resolve_tests_root
from scaffold_ca_python.factory.dependencies import AIOSQLITE, PSYCOPG_BINARY, PYDANTIC_SETTINGS, SQLALCHEMY
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory

if TYPE_CHECKING:
    from scaffold_ca_python.core.module_builder import ModuleBuilder

_CONFTEST_FIXTURE = """\


@pytest.fixture(autouse=True)
def sqlalchemy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SQLALCHEMY_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
"""

_CONFTEST_MARKER = "sqlalchemy_env"


class DrivenAdapterSqlAlchemy(DrivenAdapterFactory):
    """Factory for SQLAlchemy async driven-adapter type."""

    description: ClassVar[str] = "Async SQL (SQLAlchemy 2 async engine)"
    fixed_name: ClassVar[str] = "sqlalchemy"
    template_pkg: ClassVar[str] = "driven_adapter/sqlalchemy"
    src_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("__init__.py", "__init__.py.jinja2"),
        ("sqlalchemy_settings.py", "sqlalchemy_settings.py.jinja2"),
        ("sqlalchemy_config.py", "sqlalchemy_config.py.jinja2"),
        ("sqlalchemy_models.py", "sqlalchemy_models.py.jinja2"),
        ("sqlalchemy_repository.py", "sqlalchemy_repository.py.jinja2"),
    )
    test_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("test_sqlalchemy_adapter.py", "test_sqlalchemy_adapter.py.jinja2"),
    )
    runtime_dependencies: ClassVar[tuple[str, ...]] = (PYDANTIC_SETTINGS, SQLALCHEMY)
    test_group_dependencies: ClassVar[tuple[str, ...]] = (AIOSQLITE,)

    def build_extra(self, builder: ModuleBuilder, ctx: dict[str, object]) -> None:
        del ctx
        from scaffold_ca_python.commands.generate_driven_adapter import DbDriver

        driver = builder.get_param("driver", default=DbDriver.postgresql)
        if driver == DbDriver.sqlite:
            builder.add_dependency(AIOSQLITE)
        else:
            builder.add_dependency(PSYCOPG_BINARY)

        conftest_path = resolve_tests_root(builder.project_root) / "conftest.py"
        self.append_env_fixture(builder, conftest_path, _CONFTEST_MARKER, _CONFTEST_FIXTURE)
