"""
Funciones de utilidad genéricas para la aplicación.
"""
import datetime
import uuid
import json
from typing import Any, Dict, Optional, Union


def generate_uuid() -> str:
    """
    Genera un UUID único

    Returns:
        str: UUID en formato string
    """
    return str(uuid.uuid4())


def get_utc_now() -> datetime.datetime:
    """
    Obtiene la fecha y hora actual en UTC

    Returns:
        datetime.datetime: Fecha y hora actual en UTC
    """
    return datetime.datetime.now(datetime.timezone.utc)


def format_datetime(
    dt: datetime.datetime, format_str: str = "%Y-%m-%d %H:%M:%S"
) -> str:
    """
    Formatea una fecha y hora

    Args:
        dt (datetime.datetime): Fecha y hora a formatear
        format_str (str, optional): Formato de salida. Defaults to "%Y-%m-%d %H:%M:%S".

    Returns:
        str: Fecha y hora formateada
    """
    return dt.strftime(format_str)


def to_dict(obj: Any) -> Dict:
    """
    Convierte un objeto a diccionario

    Args:
        obj (Any): Objeto a convertir

    Returns:
        Dict: Diccionario resultante
    """
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    elif hasattr(obj, "_asdict"):
        return obj._asdict()
    else:
        return obj


def safe_json_serialize(obj: Any) -> Dict:
    """
    Serializa un objeto a JSON de manera segura

    Args:
        obj (Any): Objeto a serializar

    Returns:
        Dict: Objeto serializable en JSON
    """
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    elif isinstance(obj, datetime.date):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        return str(obj)


def parse_json(json_str: str, default: Optional[Dict] = None) -> Union[Dict, Any]:
    """
    Parsea una cadena JSON a un objeto Python

    Args:
        json_str (str): Cadena JSON a parsear
        default (Optional[Dict], optional): Valor por defecto si hay error. Defaults to None.

    Returns:
        Union[Dict, Any]: Objeto Python resultante o valor por defecto
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default if default is not None else {}
