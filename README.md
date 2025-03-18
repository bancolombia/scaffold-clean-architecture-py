# Clean Architecture Scaffold para Microservicios en Python

[![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blue)](https://python-poetry.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

## Descripción General

Estructura base para microservicios en Python siguiendo los principios de Arquitectura Limpia (Clean Architecture). Este proyecto incluye FastAPI, inyección de dependencias con dependency-injector, configuración por entorno, logging estructurado, conexión a base de datos PostgreSQL y monitoreo con OpenTelemetry.

## Arquitectura del Proyecto

### Clean Architecture

Este proyecto sigue los principios de Clean Architecture propuestos por Robert C. Martin. La arquitectura se organiza en capas concéntricas:

![Clean Architecture](https://blog.cleancoder.com/uncle-bob/images/2012-08-13-the-clean-architecture/CleanArchitecture.jpg)

1. **Entidades (Core/Domain)**: Contiene las reglas de negocio y entidades centrales.
2. **Casos de Uso (Application)**: Implementa la lógica de aplicación específica.
3. **Adaptadores de Interfaz (Interface Adapters)**: Convierte datos entre casos de uso y entidades externas.
4. **Frameworks y Drivers (Infrastructure)**: Contiene herramientas y frameworks como bases de datos, frameworks web, etc.

### Beneficios en este proyecto

- **Independencia de frameworks**: El core del sistema no depende de la existencia de bibliotecas externas.
- **Testabilidad**: Las reglas de negocio pueden probarse sin UI, base de datos, servidor web u otro elemento externo.
- **Independencia de UI**: La interfaz de usuario puede cambiar fácilmente sin cambiar el resto del sistema.
- **Independencia de bases de datos**: Las reglas de negocio no están vinculadas a una base de datos específica.
- **Independencia de agentes externos**: El core del sistema no conoce nada sobre el mundo exterior.

## Instalación y Configuración

### Requisitos previos

- Python 3.9 o superior
- [Poetry](https://python-poetry.org/) para la gestión de dependencias
- Git (opcional, para clonar el repositorio)

### Uso de Poetry

#### Instalación de Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

#### Instalación de dependencias

Clone el repositorio e instale las dependencias:

```bash
git clone https://github.com/jarciahdz/scaffold-python.git
cd scaffold-python
poetry install
```

#### Activación del entorno virtual

```bash
poetry shell
```

### Configuración del Proyecto

#### El directorio `config/`

El directorio `config/` contiene todos los archivos de configuración del proyecto organizados en archivos YAML:

- `config/`: Directorio principal de configuración
  - `settings.yaml`: Configuración general de la aplicación
  - `settings.development.yaml`: Configuración para desarrollo
  - `settings.production.yaml`: Configuración para producción
  - `settings.test.yaml`: Configuración para pruebas

#### Ejemplo de archivo YAML de configuración

Ejemplo de `config/settings.yaml`:

```yaml
application:
  name: clean-architecture-service

api:
  host: 0.0.0.0
  port: 5001
  debug: true

database:
  driver: postgresql
  host: ${DB_HOST:-localhost}
  port: ${DB_PORT:-5432}
  user: ${DB_USER:-postgres}
  password: ${DB_PASSWORD:-}
  database: ${DB_NAME:-clean_arch_db}
  params: {}

monitoring:
  enabled: false

logging:
  level: INFO
  json_format: true
```

#### Personalización de configuración

Para modificar la configuración según sus necesidades:

1. Copie los archivos YAML de ejemplo a sus versiones locales
   ```bash
   cp config/settings.yaml.example config/settings.yaml
   ```
2. Edite los archivos según sea necesario
3. Para valores sensibles, utilice variables de entorno en lugar de hardcodear valores

## Uso

### Ejecución del proyecto

Para ejecutar la aplicación principal:

```bash
poetry run uvicorn src.application.main:app --reload --host 0.0.0.0 --port 5001
```

O desde dentro del entorno virtual de Poetry:

```bash
uvicorn src.application.main:app --reload --host 0.0.0.0 --port 5001
```

### Ejemplos básicos

```python
# Ejemplo de uso de un caso de uso desde código cliente
from src.domain.usecase.health_check import HealthCheckUseCase
from src.infrastructure.adapters.postgres_adapter import PostgresAdapter
from src.application.logging_config import LoggingConfig

# Inicializar dependencias
config = {
    "host": "localhost",
    "port": 5432,
    "database": "clean_arch_db",
    "user": "postgres",
    "password": ""
}
logger = LoggingConfig(config).get_logger("example")
database = PostgresAdapter(config, logger)
health_check_use_case = HealthCheckUseCase(database, logger)

# Ejecutar caso de uso
health_status = health_check_use_case.execute()
print(f"Estado de salud: {health_status['status']}")
```

## Estructura del Código

La estructura del proyecto sigue los principios de Clean Architecture:

```
src/
├── domain/             # Entidades y reglas de negocio centrales
│   ├── model/          # Modelos de dominio
│   ├── ports/          # Interfaces (puertos) que definen contratos para la infraestructura
│   └── usecase/        # Casos de uso que orquestan la lógica de la aplicación
│
├── infrastructure/     # Implementaciones concretas de interfaces y adaptadores
│   ├── adapters/       # Adaptadores para bases de datos u otros servicios externos
│   ├── entrypoints/    # Puntos de entrada como APIs REST
│   ├── helpers/        # Utilidades y funciones auxiliares
│   ├── logging/        # Configuración de logging
│   └── monitoring/     # Configuración e instrumentación para monitoreo y telemetría
│
├── application/        # Coordinación de flujos entre dominio e infraestructura
│   ├── config.py       # Cargador de configuración
│   ├── container.py    # Contenedor de dependencias
│   ├── logging_config.py # Configuración de logging
│   ├── main.py         # Punto de entrada principal de la aplicación
│   └── monitoring_config.py # Configuración de monitoreo
```

### Responsabilidades principales

- **Domain**: Define las entidades del negocio y reglas que son independientes de cualquier framework o tecnología.
- **Application**: Contiene la lógica de aplicación específica y orquesta los flujos usando entidades del dominio.
- **Infrastructure**: Provee implementaciones concretas de las interfaces requeridas por la aplicación.
- **Interface**: Convierte los datos entre el formato conveniente para entidades externas y el formato conveniente para los casos de uso.

## Pruebas

### Pruebas unitarias

Para ejecutar las pruebas unitarias:

```bash
poetry run pytest tests/unit
```

### Pruebas de integración

Para ejecutar las pruebas de integración:

```bash
poetry run pytest tests/integration
```

### Cobertura de código

Para generar un informe de cobertura:

```bash
poetry run pytest --cov=src tests/
```

## Despliegue

### Preparación para producción

1. Asegúrese de tener todas las variables de entorno configuradas correctamente
2. Construya la aplicación para producción:

```bash
poetry install --no-dev
```

### Despliegue con Docker

Un Dockerfile básico está incluido en el proyecto. Para construir y ejecutar:

```bash
docker build -t clean-arch-python .
docker run -p 8000:8000 clean-arch-python
```

### Despliegue en servidores

1. Instale las dependencias de producción:
   ```bash
   poetry install --no-dev
   ```

2. Configure las variables de entorno para producción

3. Ejecute la aplicación:
   ```bash
   poetry run gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.application.main:app
   ```

## Contribución

Las contribuciones son bienvenidas. Por favor, siga estos pasos:

1. Fork del repositorio
2. Cree una rama para su función (`git checkout -b feature/amazing-feature`)
3. Realice sus cambios
4. Ejecute las pruebas para asegurar que todo funciona correctamente
5. Commit de sus cambios (`git commit -m 'Add some amazing feature'`)
6. Push a la rama (`git push origin feature/amazing-feature`)
7. Abra un Pull Request

### Estándares de código

Este proyecto sigue las convenciones de Python PEP 8 y utiliza herramientas de formateo y linting:

- **Black**: Para formateo de código
- **isort**: Para ordenar importaciones
- **mypy**: Para comprobación de tipos
- **flake8**: Para linting

Para ejecutar todas las verificaciones de calidad:

```bash
poetry run pre-commit run --all-files
```

## Licencia

Este proyecto está licenciado bajo la Licencia Apache 2.0 - vea el archivo [LICENSE](LICENSE) para más detalles.

## Contacto y Soporte

Para preguntas y soporte:

- Abra un issue en GitHub
- Contacte al equipo de desarrollo en: jarcia@bancolombia.com.co
- Documentación adicional: [docs/](docs/)

---

Desarrollado con ♥ utilizando Clean Architecture y las mejores prácticas de Python.