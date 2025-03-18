from dependency_injector import containers, providers
import logging

from src.domain.usecase.health_check import HealthCheckUseCase
from src.infrastructure.entrypoints.rest_api import FastAPIEntrypoint
from src.infrastructure.adapters.postgres_adapter import PostgresAdapter
from src.application.config import ConfigLoader
from src.application.logging_config import LoggingConfig
from src.application.monitoring_config import MonitoringConfig


class Container(containers.DeclarativeContainer):
    """
    Contenedor de inyección de dependencias
    """

    # Configuración
    config = providers.Singleton(ConfigLoader)

    # Logging
    logging_config = providers.Singleton(
        LoggingConfig,
        config=providers.Factory(lambda cfg: cfg.get("logging", {}), cfg=config),
    )

    logger = providers.Factory(
        lambda logging_config, name: logging_config.get_logger(name),
        logging_config=logging_config,
        name=providers.Callable(lambda: __name__),
    )

    # Base de datos
    database = providers.Singleton(
        PostgresAdapter,
        config=providers.Factory(lambda cfg: cfg.get("database", {}), cfg=config),
        logger=providers.Factory(
            lambda logging_config: logging_config.get_logger("database"),
            logging_config=logging_config,
        ),
    )

    # Monitoreo
    monitoring_config = providers.Singleton(
        MonitoringConfig,
        config=providers.Factory(lambda cfg: cfg.get("monitoring", {}), cfg=config),
        service_name=providers.Factory(
            lambda cfg: cfg.get("application", {}).get(
                "name", "clean-architecture-service"
            ),
            cfg=config,
        ),
        logger=providers.Factory(
            lambda logging_config: logging_config.get_logger("monitoring"),
            logging_config=logging_config,
        ),
    )

    # Casos de uso
    health_check_use_case = providers.Factory(
        HealthCheckUseCase,
        database=database,
        logger=providers.Factory(
            lambda logging_config: logging_config.get_logger("health_check"),
            logging_config=logging_config,
        ),
    )

    # Entrypoints
    rest_api = providers.Singleton(
        FastAPIEntrypoint,
        health_check_use_case=health_check_use_case,
        logger=providers.Factory(
            lambda logging_config: logging_config.get_logger("api"),
            logging_config=logging_config,
        ),
    )
