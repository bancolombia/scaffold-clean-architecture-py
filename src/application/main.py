import uvicorn
import logging
from fastapi import FastAPI
import os
import sys

# Agregar el directorio raíz al path para importaciones
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from src.application.container import Container


def create_app() -> FastAPI:
    """
    Crea y configura la aplicación FastAPI

    Returns:
        FastAPI: Aplicación configurada
    """
    # Configurar el contenedor de inyección de dependencias
    container = Container()

    # Cargar configuración
    config = container.config()
    config.load_config()

    # Configurar logging
    logging_config = container.logging_config()
    logger = logging_config.get_logger("main")
    logger.info("Initializing application")

    # Obtener la aplicación FastAPI
    app = container.rest_api().app

    # Configurar monitoreo si está habilitado
    monitoring_config = container.monitoring_config()

    if config.get("monitoring.enabled", False):
        monitoring_config.instrument_fastapi(app)

    logger.info("Application initialized successfully")
    return app


# Esta es la variable que Uvicorn está buscando
app = create_app()


if __name__ == "__main__":
    # Obtener la configuración
    container = Container()
    config = container.config()
    config.load_config()

    # Obtener configuración del servidor
    host = config.get("api.host", "0.0.0.0")
    port = int(config.get("api.port", 5001))
    debug = config.get("api.debug", False)

    # Iniciar el servidor
    uvicorn.run(
        "src.application.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
    )
