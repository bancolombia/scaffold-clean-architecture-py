import logging
from typing import Dict, Any
from fastapi import FastAPI
import os


class MonitoringConfig:
    """
    Configuración para monitoreo y telemetría con OpenTelemetry
    """

    def __init__(
        self, config: Dict[str, Any], service_name: str, logger: logging.Logger
    ):
        """
        Inicializa la configuración de monitoreo

        Args:
            config: Configuración de monitoreo
            service_name: Nombre del servicio para telemetría
            logger: Logger para operaciones de telemetría
        """
        self.config = config
        self.service_name = service_name
        self.logger = logger
        self.enabled = self.config.get("enabled", False)
        self.logger.info(
            f"Monitoring configuration initialized. Enabled: {self.enabled}"
        )

    def instrument_fastapi(self, app: FastAPI) -> None:
        """
        Instrumenta una aplicación FastAPI con OpenTelemetry

        Args:
            app: Aplicación FastAPI a instrumentar
        """
        # Si el monitoreo está deshabilitado, no realizar ninguna acción
        if not self.enabled:
            self.logger.info("Monitoring is disabled. Skipping instrumentation.")
            return

        try:
            self.logger.info("Instrumenting FastAPI application with OpenTelemetry")

            # Importaciones condicionales para evitar problemas si las dependencias no están instaladas
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            # Instrumentar FastAPI
            FastAPIInstrumentor.instrument_app(app)

        except ImportError as e:
            self.logger.warning(f"OpenTelemetry instrumentation skipped: {str(e)}")
        except Exception as e:
            self.logger.error(
                f"Error instrumenting FastAPI with OpenTelemetry: {str(e)}"
            )
