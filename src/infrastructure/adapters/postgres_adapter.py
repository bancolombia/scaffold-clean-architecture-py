import psycopg2
import logging
from typing import Dict, Any, Optional

from src.domain.ports.database_port import DatabasePort


class PostgresAdapter(DatabasePort):
    """
    Adaptador para PostgreSQL que implementa la interfaz DatabasePort
    """

    def __init__(self, config: Dict[str, Any], logger: logging.Logger):
        """
        Inicializa el adaptador con la configuración y logger

        Args:
            config: Configuración de la base de datos
            logger: Logger para operaciones de base de datos
        """
        self.config = config
        self.logger = logger
        self.connection = None
        # Obtener la bandera de habilitación con valor por defecto True
        self.enabled = config.get("enabled", True)
        self.logger.info(
            f"PostgreSQL adapter initialized with host: {self.config.get('host', 'default')}, enabled: {self.enabled}"
        )

    def _connect(self) -> None:
        """
        Establece una conexión a la base de datos

        Raises:
            Exception: Si hay un error al conectar
        """
        # Si la base de datos está deshabilitada, no intentamos conectar
        if not self.enabled:
            self.logger.info("Database is disabled, skipping connection")
            return

        if self.connection is None or self.connection.closed:
            try:
                # Extraer parámetros explícitos
                host = self.config.get("host")
                port = self.config.get("port")
                database = self.config.get("database")
                user = self.config.get("user")
                password = self.config.get("password")

                # Extraer parámetros adicionales si existen
                params = self.config.get("params", {})

                # Construir cadena de conexión
                connection_params = {
                    "host": host,
                    "port": port,
                    "dbname": database,
                    "user": user,
                    "password": password,
                    **params,  # Esto asegura que todos los parámetros en 'params' se apliquen
                }

                self.logger.debug(f"Connecting to PostgreSQL at {host}:{port}")
                self.connection = psycopg2.connect(**connection_params)
                self.logger.info(
                    f"Successfully connected to PostgreSQL at {host}:{port}"
                )
            except Exception as e:
                self.logger.error(f"Error connecting to database: {str(e)}")
                raise

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Ejecuta una consulta y retorna los resultados

        Args:
            query: Consulta SQL
            params: Parámetros para la consulta

        Returns:
            list: Resultados de la consulta

        Raises:
            Exception: Si hay un error al ejecutar la consulta
        """
        # Si la base de datos está deshabilitada, devolvemos una lista vacía
        if not self.enabled:
            self.logger.info(f"Database is disabled, skipping query: {query}")
            return []

        self._connect()
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            if cursor.description:
                columns = [desc[0] for desc in cursor.description]
                result = [dict(zip(columns, row)) for row in cursor.fetchall()]
                return result
            return []
        except Exception as e:
            self.logger.error(f"Error executing query: {str(e)}")
            raise
        finally:
            self.connection.commit()

    def health_check(self) -> dict:
        """
        Verifica la conexión a la base de datos

        Returns:
            dict: Estado de la base de datos con claves 'status' y 'message'
        """
        # Si la base de datos está deshabilitada, devolvemos un estado OK con mensaje informativo
        if hasattr(self, "enabled") and not self.enabled:
            self.logger.info(
                "Database is disabled by configuration, reporting as healthy"
            )
            return {"status": "OK", "message": "Database is disabled by configuration"}

        try:
            self._connect()
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            self.logger.info("Database health check passed")
            return {"status": "OK", "message": "Database connection is healthy"}
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return {"status": "ERROR", "message": str(e)}
