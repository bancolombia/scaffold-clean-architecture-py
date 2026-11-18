from __future__ import annotations

from typing import ClassVar

from scaffold_ca_python.factory.dependencies import BOTO3, PYDANTIC_SETTINGS
from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory


class DrivenAdapterSecrets(DrivenAdapterFactory):
    """Factory for Secrets driven-adapter type."""

    description: ClassVar[str] = "AWS Secrets Manager (boto3)"
    fixed_name: ClassVar[str] = "secrets"
    template_pkg: ClassVar[str] = "driven_adapter/secrets"
    src_files: ClassVar[tuple[tuple[str, str], ...]] = (
        ("__init__.py", "__init__.py.jinja2"),
        ("secrets_settings.py", "secrets_settings.py.jinja2"),
        ("secrets_adapter.py", "secrets_adapter.py.jinja2"),
    )
    test_files: ClassVar[tuple[tuple[str, str], ...]] = (("test_secrets_adapter.py", "test_secrets_adapter.py.jinja2"),)
    runtime_dependencies: ClassVar[tuple[str, ...]] = (BOTO3, PYDANTIC_SETTINGS)
