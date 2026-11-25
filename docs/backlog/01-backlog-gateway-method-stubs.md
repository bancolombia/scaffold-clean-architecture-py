# Backlog: stubs de los métodos del gateway en adapters y fakes

**Estado**: pendiente, no planificado. Hoy el scaffold cubre lo necesario; esto queda como mejora futura.
**Origen**: QA de `ms_kingbooks` con el adapter `psycopg` (spec 031), 2026-11-25.
**Siguiente paso cuando se retome**: abrir una spec numerada (`/speckit-specify`) a partir de este documento.

## AS-IS

`scaffold gm --name book` genera un gateway vacío (`class BookRepository(ABC)` sin métodos). Los generadores que se enlazan a un gateway asumen ese estado y no leen sus métodos:

- `scaffold guc --uses book_repository` genera un `_FakeBookRepository` sin métodos en los tests del use case.
- `scaffold gda --type <tipo> --gateway book_repository` genera un adapter que hereda del gateway e implementa solo su método propio (`ping()`, `get()`, etc.).

Mientras el gateway esté vacío, todo pasa (es lo que cubren los e2e). Pero si el desarrollador sigue el orden natural — definir el contrato y después generar el use case y el adapter — el proyecto generado queda en rojo sin haber editado nada generado.

**Reproducción** (verificada el 2026-11-25):

```bash
scaffold ca --name demo-abc && cd demo-abc
scaffold gm --name book
# añadir a domain/model/book/gateways/book_repository.py:
#     @abstractmethod
#     async def find_all(self) -> list[Book]: ...
scaffold guc --name get_books --uses book_repository
scaffold gda --type psycopg --gateway book_repository
uv sync && uv run pytest && uv run mypy --strict src
```

Resultado:

- `TypeError: Can't instantiate abstract class PsycopgRepository without an implementation for abstract method 'find_all'` en el test de wiring (`test_container_resolves_psycopg`).
- El mismo `TypeError` con `_FakeBookRepository` en `test_get_books_usecase.py`.
- `mypy --strict`: 3 errores.

Solo se reprodujo con `psycopg`, pero por la misma razón debería afectar a todo `gda --gateway` (`rest-consumer`, `secrets`, `sqlalchemy`, `generic`): ninguna de esas plantillas genera los métodos del contrato. Hay que confirmarlo al retomar el tema.

## TO-BE

Cuando el gateway ya tiene métodos abstractos al momento de generar:

1. **Adapters (`gda --gateway`)**: el repositorio generado incluye un stub por cada método abstracto, con la misma firma (nombre, parámetros, anotaciones, `async` si aplica) y cuerpo `raise NotImplementedError`. En `psycopg` y `sqlalchemy` el stub lleva además un comentario con el patrón de acceso del adapter (por ejemplo `async with self._pool.connection() as conn, conn.cursor(row_factory=dict_row)` y parámetros `%s`).
2. **Fakes de use case (`guc --uses`)**: `_Fake<Gateway>` implementa los mismos métodos con `raise NotImplementedError`, de modo que se pueda instanciar y cada test sobrescriba solo lo que use.
3. **Un test por stub**: el test generado del adapter incluye, por cada método, un test que comprueba que lanza `NotImplementedError`. No se generan tests con SQL ni respuestas inventadas: el test solo fija que el método existe y todavía no está implementado, y el desarrollador lo reemplaza al implementarlo.

Resultado esperado: con el gateway ya definido, el proyecto generado vuelve a pasar `ruff`, `mypy --strict`, `pytest` y `scaffold vs` sin ediciones.

## Alcance

**Dentro**
- Leer los métodos abstractos del gateway con `ast` (el gateway se localiza con `find_gateway` en `src/scaffold_ca_python/commands/_shared.py`).
- Pasar la lista de métodos al contexto de las plantillas (`DrivenAdapterFactory.adapter_context` en `factory/driven_adapters/base.py` y la factory de use cases).
- Importar en el archivo generado los tipos que usan las firmas (p. ej. `Book`), reutilizando los imports del módulo del gateway.

**Fuera**
- Generar SQL, DDL o mapeos reales.
- Sincronizar métodos añadidos al gateway **después** de generar el adapter; eso sigue siendo trabajo manual (o un futuro comando de actualización).
- Tests de integración contra una base de datos real.

## Archivos que tocaría

| Área | Archivos |
|---|---|
| Lectura del contrato | `src/scaffold_ca_python/commands/_shared.py` (`find_gateway`) o un helper nuevo en `core/` |
| Contexto de plantillas | `src/scaffold_ca_python/factory/driven_adapters/base.py` (`adapter_context`), factory de use cases en `factory/simple/` |
| Adapters | `templates/driven_adapter/{generic/adapter,rest_consumer/rest_consumer,secrets/secrets_adapter,sqlalchemy/sqlalchemy_repository,psycopg/psycopg_repository}.py.jinja2` y sus tests |
| Fakes de use case | `templates/use_case/test_use_case.py.jinja2`, `templates/use_case/test_use_case_factory.py.jinja2` |
| Tests del CLI | `tests/templates/`, `tests/factory/driven_adapters/`, `tests/commands/test_generate_use_case.py` |
| e2e | nuevo escenario en `tests/e2e/test_generated_project_quality.py`: gateway con métodos → `guc` → `gda psycopg` → quality checks en verde |

## Criterios de aceptación (borrador)

- Con un gateway que declara N métodos abstractos (sync y async, con y sin parámetros), `gda --gateway` genera N stubs con firma idéntica y `raise NotImplementedError`.
- `guc --uses` genera un fake instanciable con los mismos N métodos.
- El test generado del adapter incluye N tests que comprueban el `NotImplementedError`.
- Con un gateway vacío, la salida es idéntica a la actual (el baseline de dry-run no cambia).
- La reproducción de arriba termina con `pytest` y `mypy --strict` en verde.

## Preguntas abiertas

- ¿Qué hacer con firmas cuyos tipos no se pueden resolver desde el módulo del gateway (imports relativos, `TYPE_CHECKING`)? Opción por defecto: copiar los imports del gateway tal cual.
- ¿Los métodos no abstractos del gateway (con implementación por defecto) se ignoran? Propuesta: sí.
- ¿Tiene sentido un aviso en `vs` cuando un adapter no implementa todos los métodos de su gateway? Solo si los stubs no cubren el caso de métodos añadidos después.
