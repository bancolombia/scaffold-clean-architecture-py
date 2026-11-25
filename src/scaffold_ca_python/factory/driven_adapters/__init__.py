"""Driven-adapter factory registry."""

from __future__ import annotations

from scaffold_ca_python.factory.driven_adapters.base import DrivenAdapterFactory
from scaffold_ca_python.factory.driven_adapters.da_generic import DrivenAdapterGeneric
from scaffold_ca_python.factory.driven_adapters.da_psycopg import DrivenAdapterPsycopg
from scaffold_ca_python.factory.driven_adapters.da_rest_consumer import DrivenAdapterRestConsumer
from scaffold_ca_python.factory.driven_adapters.da_secrets import DrivenAdapterSecrets
from scaffold_ca_python.factory.driven_adapters.da_sqlalchemy import DrivenAdapterSqlAlchemy

DRIVEN_ADAPTER_FACTORIES: dict[str, type[DrivenAdapterFactory]] = {
    "rest-consumer": DrivenAdapterRestConsumer,
    "secrets": DrivenAdapterSecrets,
    "generic": DrivenAdapterGeneric,
    "sqlalchemy": DrivenAdapterSqlAlchemy,
    "psycopg": DrivenAdapterPsycopg,
}
