import logging
import json
import os
import sys
from typing import Dict, Any
from datetime import datetime


class JsonFormatter(logging.Formatter):
    """
    Formateador personalizado para logs en formato JSON
    """

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Agregar excepciones si existen
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Agregar datos adicionales del registro si existen
        if hasattr(record, "data") and isinstance(record.data, dict):
            for key, value in record.data.items():
                log_data[key] = value

        return json.dumps(log_data)


class LoggerFactory:
    """
    Fábrica para crear y configurar loggers
    """

    @staticmethod
    def create_logger(name: str, config: Dict[str, Any]) -> logging.Logger:
        """
        Crea y configura un logger

        Args:
            name (str): Nombre del logger
            config (Dict[str, Any]): Configuración del logger

        Returns:
            logging.Logger: Logger configurado
        """
        logger = logging.getLogger(name)

        # Si ya está configurado, devolverlo
        if logger.handlers:
            return logger

        # Configuración del nivel de log
        level = getattr(logging, config.get("level", "INFO").upper())
        logger.setLevel(level)

        # Configurar handler para la consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        # Utilizar el formateador JSON o uno estándar según la configuración
        if config.get("json_format", True):
            formatter = JsonFormatter()
        else:
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # Configurar handler para archivos si existe la ruta
        file_path = config.get("file_path")
        if file_path:
            # Asegurarse de que el directorio existe
            os.makedirs(file_path, exist_ok=True)

            file_name = f"{name.replace('.', '_')}.log"
            file_handler = logging.FileHandler(os.path.join(file_path, file_name))
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        logger.propagate = False
        return logger
