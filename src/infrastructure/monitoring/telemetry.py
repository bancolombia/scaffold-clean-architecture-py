from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI


class TelemetryManager:
    """
    Gestiona la configuración y uso de OpenTelemetry para monitoreo y trazabilidad
    """

    def __init__(
        self,
        config: Dict[str, Any],
        service_name: str,
        logger: Optional[logging.Logger] = None,
    ):
        self.config = config
        self.service_name = service_name
        self.logger = logger or logging.getLogger(__name__)
        self._tracer_provider = None
        self.enabled = config.get("enabled", False)

        if self.enabled:
            self._setup_telemetry()

    def _setup_telemetry(self):
        """Configura el sistema de telemetría con OpenTelemetry"""
        try:
            self.logger.info("Setting up OpenTelemetry telemetry")

            # Configurar el proveedor de trazas con el nombre del servicio
            resource = Resource(attributes={SERVICE_NAME: self.service_name})

            self._tracer_provider = TracerProvider(resource=resource)
            trace.set_tracer_provider(self._tracer_provider)

            # Configurar el exportador para Dynatrace si está disponible
            dynatrace_config = self.config.get("dynatrace", {})
            if dynatrace_config:
                endpoint = f"{dynatrace_config.get('tenant_url')}/api/v2/otlp/v1/traces"
                headers = {
                    "Authorization": f"Api-Token {dynatrace_config.get('api_token')}"
                }

                self.logger.info(
                    f"Configuring OTLP exporter for Dynatrace at {endpoint}"
                )
                otlp_exporter = OTLPSpanExporter(endpoint=endpoint, headers=headers)

                # Configurar el procesador de spans
                span_processor = BatchSpanProcessor(otlp_exporter)
                self._tracer_provider.add_span_processor(span_processor)

            # Instrumentar psycopg2 para trazas automáticas
            Psycopg2Instrumentor().instrument()

            self.logger.info("OpenTelemetry telemetry setup completed")
        except Exception as e:
            self.logger.error(f"Failed to setup telemetry: {str(e)}")
            self.enabled = False

    def instrument_fastapi(self, app: FastAPI):
        """
        Instrumenta una aplicación FastAPI para trazas automáticas

        Args:
            app (FastAPI): Aplicación FastAPI a instrumentar
        """
        if not self.enabled:
            self.logger.info("Telemetry is disabled, skipping FastAPI instrumentation")
            return

        try:
            self.logger.info("Instrumenting FastAPI application with OpenTelemetry")
            FastAPIInstrumentor.instrument_app(app)
        except Exception as e:
            self.logger.error(f"Failed to instrument FastAPI: {str(e)}")
