"""libcst transforms used by the dependency-injector → wireup action."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from scaffold_ca_python.factory.upgrades.actions.di_wireup import codemod


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
    return path


_ADAPTER = '''
"""Adapter docstring."""

from __future__ import annotations

from app.domain.model.book.gateways.book_repository import BookRepository


class BookStoreAdapter(BookRepository):
    pass
'''


def test_add_injectable_places_import_after_docstring_and_future() -> None:
    out = codemod.add_injectable(
        textwrap.dedent(_ADAPTER).lstrip(),
        "BookStoreAdapter",
        as_type=("app.domain.model.book.gateways.book_repository", "BookRepository"),
        lifetime="singleton",
    )
    assert out is not None
    compile(out, "adapter.py", "exec")
    assert out.startswith('"""Adapter docstring."""\n\nfrom __future__ import annotations\n')
    assert "@wireup.injectable(as_type=BookRepository)\nclass BookStoreAdapter" in out
    assert out.count("import wireup") == 1


def test_add_injectable_adds_missing_as_type_import_and_lifetime() -> None:
    out = codemod.add_injectable(
        "class Adapter:\n    pass\n",
        "Adapter",
        as_type=("app.domain.model.x.gateways.repo", "Repo"),
        lifetime="transient",
    )
    assert out is not None
    assert "from app.domain.model.x.gateways.repo import Repo" in out
    assert '@wireup.injectable(as_type=Repo, lifetime="transient")' in out


def test_add_injectable_is_idempotent() -> None:
    once = codemod.add_injectable("class A:\n    pass\n", "A", as_type=None, lifetime="singleton")
    assert once is not None
    assert codemod.add_injectable(once, "A", as_type=None, lifetime="singleton") is None


_CONTROLLER = """
from __future__ import annotations

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends

from app.application.config.container import Container
from app.domain.usecase.get_book_usecase import GetBookUseCase

router = APIRouter()


@router.get("/books/{book_id}")
@inject
async def get_book(
    book_id: str,
    use_case: GetBookUseCase = Depends(Provide[Container.usecase_container.get_book]),
) -> str:
    return book_id


@inject
def plain(use_case: GetBookUseCase = Provide[Container.usecase_container.get_book]) -> None:
    pass
"""


def test_rewrite_injections_uses_annotated_type_and_cleans_imports() -> None:
    result = codemod.rewrite_injections(textwrap.dedent(_CONTROLLER).lstrip(), "app.application.config.container")
    assert result.converted == 2
    assert result.unresolved == []
    out = result.source
    compile(out, "controller.py", "exec")
    assert "use_case: Injected[GetBookUseCase]" in out
    assert "Provide" not in out and "@inject" not in out and "Container" not in out
    assert "Depends" not in out
    assert "from wireup import Injected" in out


def test_rewrite_injections_keeps_depends_when_still_used() -> None:
    source = (
        "from dependency_injector.wiring import Provide, inject\n"
        "from fastapi import Depends\n\n"
        "def other() -> int:\n    return 1\n\n"
        "@inject\n"
        "def f(uc: UseCase = Depends(Provide['uc']), x: int = Depends(other)) -> None:\n    pass\n"
    )
    out = codemod.rewrite_injections(source, "app.application.config.container").source
    compile(out, "f.py", "exec")
    assert "from fastapi import Depends" in out
    assert "uc: Injected[UseCase], x: int = Depends(other)" in out


def test_rewrite_injections_leaves_param_after_default_as_unresolved() -> None:
    source = (
        "from dependency_injector.wiring import Provide\n\n\n"
        "def f(q: str = 'a', uc: UseCase = Provide['uc']) -> None:\n    pass\n"
    )
    result = codemod.rewrite_injections(source, "app.application.config.container")
    compile(result.source, "f.py", "exec")
    assert result.converted == 0
    assert result.unresolved == [4]
    assert "Provide['uc']" in result.source


def test_rewrite_injections_reports_unannotated_parameters() -> None:
    source = "from dependency_injector.wiring import Provide\n\n\ndef f(uc=Provide['uc']) -> None:\n    pass\n"
    result = codemod.rewrite_injections(source, "app.application.config.container")
    assert result.converted == 0
    assert result.unresolved == [4]


def test_analyze_containers_maps_providers_to_kinds(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "resource_container.py",
        """
        from dependency_injector import containers, providers

        from app.infrastructure.helpers.clock import Clock, open_clock


        class ResourceContainer(containers.DeclarativeContainer):
            config = providers.Configuration()
            clock = providers.Resource(open_clock)
            pick = providers.Selector(config.mode, a=providers.Object(1))
            call = providers.Callable(open_clock)
            clock_factory = providers.Factory(Clock)
            with_args = providers.Singleton(Clock, 1)
            nested = providers.Container(OtherContainer)

            class Inner(containers.DeclarativeContainer):
                pass
        """,
    )
    analysis = codemod.analyze_containers([path])
    kinds = {(f.kind, f.line) for f in analysis.findings}
    assert kinds == {
        ("configuration_provider", 7),
        ("resource_provider", 8),
        ("selector_provider", 9),
        ("callable_provider", 10),
        ("provider_arguments", 12),
        ("nested_container", 13),
        ("nested_container", 15),
    }
    [binding] = analysis.bindings
    assert (binding.name, binding.class_name, binding.lifetime) == ("clock_factory", "Clock", "transient")
    assert binding.module == "app.infrastructure.helpers.clock"


def test_analyze_containers_ignores_commented_examples(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "resource_container.py",
        """
        from dependency_injector import containers, providers  # noqa: F401


        class ResourceContainer(containers.DeclarativeContainer):
            # db_pool = providers.Resource(
            #     MyResource,
            # )
            pass
        """,
    )
    analysis = codemod.analyze_containers([path])
    assert analysis.findings == [] and analysis.bindings == []


def test_analyze_containers_accepts_known_sub_containers(tmp_path: Path) -> None:
    sub = _write(
        tmp_path,
        "da_container.py",
        "from dependency_injector import containers\n\n\n"
        "class DAContainer(containers.DeclarativeContainer):\n    pass\n",
    )
    root = _write(
        tmp_path,
        "container.py",
        """
        from dependency_injector import containers, providers


        class Container(containers.DeclarativeContainer):
            da_container = providers.Container(DAContainer)
            deps = providers.DependenciesContainer()
        """,
    )
    assert codemod.analyze_containers([root, sub]).findings == []


def test_class_init_params_resolve_annotation_imports(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "uc.py",
        """
        from app.domain.model.book.gateways.book_repository import BookRepository


        class GetBookUseCase:
            def __init__(self, book_repository: BookRepository, retries: int = 3) -> None:
                pass
        """,
    )
    params = codemod.class_init_params(path, "GetBookUseCase")
    assert params is not None
    assert [(p.name, p.annotation, p.has_default) for p in params] == [
        ("book_repository", "BookRepository", False),
        ("retries", "int", True),
    ]
    assert params[0].imports == (("app.domain.model.book.gateways.book_repository", "BookRepository"),)
    assert codemod.class_init_params(path, "Missing") is None


@pytest.mark.parametrize("lifetime", ["singleton", "transient"])
def test_render_factory_compiles(lifetime: str) -> None:
    params = [codemod.InitParam("repo", "Repo", (("app.domain.model.x.gateways.repo", "Repo"),), False)]
    out = codemod.render_factory(
        usecase_module="app.domain.usecase.do_usecase", class_name="DoUseCase", params=params, lifetime=lifetime
    )
    compile(out, "factory.py", "exec")
    assert "def do_usecase_factory(" in out
    assert ("lifetime=" in out) is (lifetime == "transient")


def test_override_lines_ignore_docstrings() -> None:
    source = (
        '"""Example: app.state.container.svc.override(Mock())."""\n'
        "def test_x(app):\n"
        "    app.state.container.svc.override(1)\n"
    )
    assert codemod.override_lines(source) == [3]
