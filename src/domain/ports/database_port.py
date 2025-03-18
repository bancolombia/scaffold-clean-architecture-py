from abc import ABC, abstractmethod
from typing import Any, Dict


class DatabasePort(ABC):
    """
    Puerto para la interacción con la base de datos
    """

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Verifica la salud de la conexión a la base de datos

        Returns:
            Dict[str, Any]: Estado de la base de datos con claves 'status' y 'message'
        """
        pass

    @abstractmethod
    def execute_query(self, query: str, params: dict = None) -> Any:
        """
        Ejecuta una consulta en la base de datos

        Args:
            query (str): Consulta SQL a ejecutar
            params (dict, optional): Parámetros para la consulta. Defaults to None.

        Returns:
            Any: Resultado de la consulta
        """
        pass
