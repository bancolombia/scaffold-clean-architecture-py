import logging
from typing import Dict, Any
from src.infrastructure.logging.logger_factory import LoggerFactory


class LoggingConfig:
    """
    Configuración centralizada del sistema de logging
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Inicializa la configuración de logging

        Args:
            config (Dict[str, Any]): Configuración de logging
        """
        self.config = config
        self._setup_root_logger()

    def _setup_root_logger(self):
        """
        Configura el logger raíz
        """
        # Limpiar handlers existentes
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Crear y configurar el logger raíz
        LoggerFactory.create_logger("root", self.config)

        # Configurar loggers de terceros
        third_party_loggers = ["uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"]

        for logger_name in third_party_loggers:
            logger = logging.getLogger(logger_name)
            logger.handlers = []  # Eliminar handlers existentes
            logger.propagate = True  # Propagar al logger raíz

    def get_logger(self, name: str) -> logging.Logger:
        """
        Obtiene un logger configurado

        Args:
            name (str): Nombre del logger

        Returns:
            logging.Logger: Logger configurado
        """
        return LoggerFactory.create_logger(name, self.config)
