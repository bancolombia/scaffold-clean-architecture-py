"""Template rendering tests for driven_adapter/ group — all 3 types."""

from scaffold_ca_python.models.context import ModuleContext, ProjectContext
from tests.helpers import read_template as _tmpl
from tests.helpers import renderer


def _project() -> ProjectContext:
    return ProjectContext(name="my-app")


def _ctx(name: str = "my-adapter") -> ModuleContext:
    return ModuleContext(name=name, project=_project())


# rest-consumer


def test_rest_consumer_has_httpx_import() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/rest_consumer/rest_consumer.py.jinja2"), _ctx().model_dump())
    assert "httpx" in out


def test_rest_consumer_has_async_client() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/rest_consumer/rest_consumer.py.jinja2"), _ctx().model_dump())
    assert "AsyncClient" in out


def test_rest_consumer_has_async_get() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/rest_consumer/rest_consumer.py.jinja2"), _ctx().model_dump())
    assert "async def get" in out


def test_rest_consumer_config_yields_async_client() -> None:
    out = renderer.render_string(
        _tmpl("driven_adapter/rest_consumer/rest_consumer_config.py.jinja2"),
        _ctx().model_dump(),
    )
    assert "async def rest_consumer_client" in out
    assert "yield client" in out
    assert "await client.aclose()" in out


# secrets


def test_secrets_has_get_secret() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/secrets/secrets_adapter.py.jinja2"), _ctx().model_dump())
    assert "get_secret" in out


def test_secrets_has_async_methods() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/secrets/secrets_adapter.py.jinja2"), _ctx().model_dump())
    assert "async def" in out


# generic


def test_generic_class_name_present() -> None:
    ctx = _ctx("payment-gateway")
    out = renderer.render_string(_tmpl("driven_adapter/generic/adapter.py.jinja2"), ctx.model_dump())
    assert "PaymentGateway" in out


def test_generic_has_adapter_suffix() -> None:
    ctx = _ctx("payment-gateway")
    out = renderer.render_string(_tmpl("driven_adapter/generic/adapter.py.jinja2"), ctx.model_dump())
    assert "PaymentGatewayAdapter" in out


def test_generic_has_async_execute() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/generic/adapter.py.jinja2"), _ctx().model_dump())
    assert "async def execute" in out


# sqlalchemy


def test_sqlalchemy_config_has_sessionmaker_expire_on_commit_false() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/sqlalchemy/sqlalchemy_config.py.jinja2"), _ctx().model_dump())
    assert "async_sessionmaker" in out
    assert "expire_on_commit=False" in out


def test_sqlalchemy_models_has_declarative_base() -> None:
    out = renderer.render_string(_tmpl("driven_adapter/sqlalchemy/sqlalchemy_models.py.jinja2"), _ctx().model_dump())
    assert "DeclarativeBase" in out
    assert "class Base" in out


def test_sqlalchemy_repository_uses_sessionmaker() -> None:
    tpl = _tmpl("driven_adapter/sqlalchemy/sqlalchemy_repository.py.jinja2")
    out = renderer.render_string(tpl, _ctx().model_dump())
    assert "async_sessionmaker" in out or "_sessions" in out


def test_sqlalchemy_test_adapter_uses_staticpool() -> None:
    tpl = _tmpl("driven_adapter/sqlalchemy/test_sqlalchemy_adapter.py.jinja2")
    out = renderer.render_string(tpl, _ctx().model_dump())
    assert "StaticPool" in out


# psycopg


def _render_psycopg(template: str, gateway: dict[str, str] | None = None) -> str:
    ctx = _ctx("psycopg").model_dump()
    ctx["gateway"] = gateway
    return renderer.render_string(_tmpl(f"driven_adapter/psycopg/{template}"), ctx)


def test_psycopg_settings_fields_and_prefix() -> None:
    out = _render_psycopg("psycopg_settings.py.jinja2")
    assert "class PsycopgSettings(BaseSettings)" in out
    assert 'env_prefix="PSYCOPG_"' in out
    for field in ("database_url: str", "min_size: int = 1", "max_size: int = 10", "timeout: float = 30.0"):
        assert field in out


def test_psycopg_config_opens_pool_lazily() -> None:
    out = _render_psycopg("psycopg_config.py.jinja2")
    assert "_pool: AsyncConnectionPool[AsyncConnection[tuple[Any, ...]]] | None = None" in out
    assert "asyncio.Lock()" in out
    assert "open=False" in out
    assert "open(wait=True" in out
    assert "pool.connection()" in out
    init_body = out.split("def __init__", 1)[1].split("\n\n", 1)[0]
    assert "AsyncConnectionPool(" not in init_body


def test_psycopg_config_resource_closes_pool() -> None:
    out = _render_psycopg("psycopg_config.py.jinja2")
    assert "async def psycopg_pool(settings: PsycopgSettings) -> AsyncIterator[PsycopgConnectionPool]" in out
    assert "await pool.close()" in out


def test_psycopg_repository_uses_parameters_never_formatted_sql() -> None:
    out = _render_psycopg("psycopg_repository.py.jinja2")
    assert "SELECT 1" in out
    assert "dict_row" in out
    assert "%s" in out
    for forbidden in ('f"SELECT', "f'SELECT", ".format(", '" % ('):
        assert forbidden not in out


def test_psycopg_repository_binds_gateway() -> None:
    gateway = {"name": "book_repository", "class_name": "BookRepository", "model_module": "book"}
    out = _render_psycopg("psycopg_repository.py.jinja2", gateway)
    assert "@wireup.injectable(as_type=BookRepository)" in out
    assert "class PsycopgRepository(BookRepository)" in out


def test_psycopg_test_template_covers_pool_lifecycle() -> None:
    out = _render_psycopg("test_psycopg_adapter.py.jinja2")
    assert "my_app.infrastructure.driven_adapters.psycopg.psycopg_config.AsyncConnectionPool" in out
    assert "asyncio.gather" in out
    assert "PoolTimeout" in out
