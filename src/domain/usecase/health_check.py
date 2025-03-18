from src.domain.model.health_status import HealthStatus, Status
from src.domain.ports.database_port import DatabasePort
import logging


class HealthCheckUseCase:
    def __init__(self, database: DatabasePort = None, logger: logging.Logger = None):
        self.database = database
        self.logger = logger or logging.getLogger(__name__)

    def execute(self) -> dict:
        """
        Ejecuta la verificación de salud del servicio
        Returns:
            dict: Estado de salud del servicio
        """
        details = {}

        # Verificar estado de la base de datos si está disponible
        if self.database:
            try:
                # Intentar obtener el estado de la base de datos
                db_result = self.database.health_check()

                # Manejar el resultado según su tipo
                if isinstance(db_result, bool):
                    # Si es booleano, convertir al formato esperado
                    details["database"] = {"status": "OK" if db_result else "ERROR"}
                    if not db_result:
                        return HealthStatus(Status.ERROR, details).__dict__
                elif isinstance(db_result, dict):
                    # Si ya es diccionario, usarlo directamente
                    db_status = db_result.get("status", "ERROR")
                    db_message = db_result.get("message", "")

                    details["database"] = {"status": db_status}

                    if db_message:
                        details["database"]["message"] = db_message

                    if db_status == "ERROR":
                        return HealthStatus(Status.ERROR, details).__dict__
                else:
                    # Tipo no esperado
                    self.logger.error(
                        f"Unexpected database health check result type: {type(db_result)}"
                    )
                    details["database"] = {
                        "status": "ERROR",
                        "message": "Unexpected health check result type",
                    }
                    return HealthStatus(Status.ERROR, details).__dict__
            except Exception as e:
                self.logger.error(f"Database health check failed: {str(e)}")
                details["database"] = {"status": "ERROR", "message": str(e)}
                return HealthStatus(Status.ERROR, details).__dict__

        # Todo está bien
        self.logger.debug("Health check executed successfully")
        return HealthStatus(Status.OK, details).__dict__
