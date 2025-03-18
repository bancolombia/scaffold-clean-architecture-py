"""
Definición de excepciones personalizadas para la aplicación.
"""


class ApplicationError(Exception):
    """Excepción base para errores de la aplicación"""

    def __init__(self, message="An application error occurred", details=None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(ApplicationError):
    """Error en la configuración de la aplicación"""

    def __init__(self, message="Configuration error", details=None):
        super().__init__(message, details)


class DatabaseError(ApplicationError):
    """Error relacionado con la base de datos"""

    def __init__(self, message="Database error", details=None):
        super().__init__(message, details)


class ValidationError(ApplicationError):
    """Error de validación de datos"""

    def __init__(self, message="Validation error", details=None):
        super().__init__(message, details)


class NotFoundError(ApplicationError):
    """Error cuando un recurso no es encontrado"""

    def __init__(self, resource_type="Resource", resource_id=None):
        message = f"{resource_type} not found"
        details = {"resource_type": resource_type}
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, details)


class UnauthorizedError(ApplicationError):
    """Error de autenticación"""

    def __init__(self, message="Unauthorized access", details=None):
        super().__init__(message, details)


class ForbiddenError(ApplicationError):
    """Error de autorización"""

    def __init__(self, message="Forbidden access", details=None):
        super().__init__(message, details)
