import os
import yaml
import re
from typing import Dict, Any, Optional


class ConfigLoader:
    """
    Cargador de configuración desde archivos YAML con soporte para
    múltiples entornos y variables de entorno
    """

    def __init__(self):
        """
        Inicializa el cargador de configuración
        """
        self.config = {}

    def load_config(self) -> Dict[str, Any]:
        """
        Carga la configuración desde archivos YAML

        Returns:
            Dict[str, Any]: Configuración cargada
        """
        # Determinar entorno
        env = os.environ.get("ENVIRONMENT", "development")

        # Definir rutas de archivos
        base_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "config",
        )
        base_config_path = os.path.join(base_path, "settings.yaml")
        env_config_path = os.path.join(base_path, f"settings.{env}.yaml")

        # Cargar configuración base
        self.config = self._load_yaml_file(base_config_path, {})
        print(f"Loaded base config from {base_config_path}")

        # Cargar configuración específica del entorno
        if os.path.exists(env_config_path):
            env_config = self._load_yaml_file(env_config_path, {})
            print(f"Loaded environment config from {env_config_path}")
            self._deep_merge(self.config, env_config)
        else:
            print(f"Warning: Environment config file not found: {env_config_path}")

        # Procesar variables de entorno
        self._process_env_variables(self.config)

        return self.config

    def _load_yaml_file(
        self, file_path: str, default: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Carga un archivo YAML

        Args:
            file_path: Ruta al archivo YAML
            default: Valor por defecto si hay error

        Returns:
            Dict[str, Any]: Contenido del archivo YAML
        """
        if default is None:
            default = {}

        try:
            if os.path.exists(file_path):
                with open(file_path, "r") as file:
                    return yaml.safe_load(file) or default
        except Exception as e:
            print(f"Error loading config file {file_path}: {str(e)}")
        return default

    def _deep_merge(
        self, target: Dict[str, Any], source: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Combina dos diccionarios de forma recursiva

        Args:
            target: Diccionario destino
            source: Diccionario fuente

        Returns:
            Dict[str, Any]: Diccionario combinado
        """
        for key, value in source.items():
            if (
                key in target
                and isinstance(target[key], dict)
                and isinstance(value, dict)
            ):
                self._deep_merge(target[key], value)
            else:
                target[key] = value
        return target

    def _process_env_variables(self, config: Dict[str, Any]) -> None:
        """
        Reemplaza las referencias a variables de entorno en la configuración

        Args:
            config: Configuración a procesar
        """
        pattern = re.compile(r"\${([a-zA-Z0-9_]+)(:(.+?))?}")

        def replace_vars(obj):
            if isinstance(obj, str):
                match = pattern.search(obj)
                if match:
                    env_var, _, default = match.groups()
                    # Corregir para manejar el caso donde default es None
                    if default is None:
                        default = ""
                    env_value = os.environ.get(env_var, default)
                    # Asegurar que env_value sea siempre una cadena
                    if env_value is None:
                        env_value = ""
                    return obj.replace(match.group(0), env_value)
                return obj
            elif isinstance(obj, dict):
                return {k: replace_vars(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [replace_vars(i) for i in obj]
            return obj

        result = replace_vars(config)
        if isinstance(result, dict):
            self.config = result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtiene un valor de la configuración usando notación de puntos

        Args:
            key: Clave en notación de puntos (ej: "database.host")
            default: Valor por defecto si la clave no existe

        Returns:
            Any: Valor encontrado o valor por defecto
        """
        keys = key.split(".")
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value
