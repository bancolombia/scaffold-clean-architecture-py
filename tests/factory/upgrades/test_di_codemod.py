"""libcst container extraction."""

from scaffold_ca_python.core.di_container_codemod import extract_singleton_usecases


def test_extract_singleton_from_usecases_container() -> None:
    source = """
from dependency_injector import containers, providers
from my_pkg.domain.usecase.book_usecase import BookUseCase

class UseCaseContainer(containers.DeclarativeContainer):
    book = providers.Singleton(BookUseCase)
"""
    bindings, pending = extract_singleton_usecases(source, python_package="my_pkg")
    assert len(bindings) == 1
    assert bindings[0].class_name == "BookUseCase"
    assert bindings[0].usecase_module == "book_usecase"
    assert pending == []
