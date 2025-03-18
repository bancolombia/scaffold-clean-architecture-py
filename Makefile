.PHONY: setup run run-no-db test test-cov lint format clean menu help

# Menú principal
menu:
	@clear
	@echo "╔══════════════════════════════════════════════╗"
	@echo "║            CENTRO DE COMANDOS DEVOPS         ║"
	@echo "╚══════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 1. Configurar Proyecto    (poetry install)"
	@echo "🔥 2. Ejecutar Aplicación    (uvicorn)"
	@echo "⚡ 3. Ejecutar Sin BD         (ENVIRONMENT=no-db)"
	@echo "🧪 4. Ejecutar Pruebas       (pytest)"
	@echo "📊 5. Cobertura de Pruebas   (pytest --cov)"
	@echo "🔍 6. Revisar Código         (flake8)"
	@echo "✨ 7. Formatear Código       (black)"
	@echo "🧹 8. Limpiar Proyecto       (eliminar archivos temporales)"
	@echo "🔄 9. Limpiar y Configurar   (clean + setup)"
	@echo "❓ h. Ayuda                  (mostrar comandos)"
	@echo "❌ 0. Salir"
	@echo ""
	@read -p "Ingresa tu opción: " choice; \
	case $$choice in \
		1) make setup ;; \
		2) make run ;; \
		3) make run-no-db ;; \
		4) make test ;; \
		5) make test-cov ;; \
		6) make lint ;; \
		7) make format ;; \
		8) make clean ;; \
		9) make clean-setup ;; \
		h) make help ;; \
		0) echo "Saliendo..."; exit 0 ;; \
		*) echo "¡Opción inválida!" ;; \
	esac
	@echo ""
	@echo "Presiona Enter para volver al menú..."
	@read
	@make menu

# Ayuda
help:
	@echo "╔══════════════════════════════════════════════╗"
	@echo "║            COMANDOS DISPONIBLES              ║"
	@echo "╚══════════════════════════════════════════════╝"
	@echo ""
	@echo "make           - Muestra el menú interactivo"
	@echo "make setup     - Configura el proyecto"
	@echo "make run       - Ejecuta la aplicación"
	@echo "make run-no-db - Ejecuta sin base de datos"
	@echo "make test      - Ejecuta pruebas"
	@echo "make test-cov  - Ejecuta pruebas con cobertura"
	@echo "make lint      - Verifica el código"
	@echo "make format    - Formatea el código"
	@echo "make clean     - Limpia archivos temporales"
	@echo "make help      - Muestra esta ayuda"
	@echo ""
	@echo "Presiona Enter para volver al menú..."
	@read
	@make menu

# Configuración del proyecto
setup:
	@echo "🚀 Configurando proyecto..."
	@poetry install
	@echo "✅ ¡Configuración completada!"

# Ejecutar aplicación
run:
	@echo "🔥 Iniciando aplicación..."
	@poetry run uvicorn src.application.main:app --reload --host 0.0.0.0 --port 5001

# Ejecutar sin base de datos
run-no-db:
	@echo "⚡ Iniciando aplicación sin base de datos..."
	@ENVIRONMENT=no-db poetry run uvicorn src.application.main:app --reload --host 0.0.0.0 --port 5001

# Ejecutar pruebas
test:
	@echo "🧪 Ejecutando pruebas..."
	@poetry run pytest
	@echo "✅ ¡Pruebas completadas!"

# Ejecutar pruebas con cobertura
test-cov:
	@echo "📊 Ejecutando pruebas con cobertura..."
	@poetry run pytest --cov=src tests/ --cov-report=term-missing --cov-report=html
	@echo "✅ ¡Pruebas de cobertura completadas!"

# Verificación de linting
lint:
	@echo "🔍 Revisando código..."
	@poetry run flake8 src tests
	@echo "✅ ¡Revisión completada!"

# Formatear código
format:
	@echo "✨ Formateando código..."
	@poetry run black src tests
	@echo "✅ ¡Formateo completado!"

# Limpiar archivos temporales
clean:
	@echo "🧹 Limpiando archivos temporales..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name "*.egg-info" -exec rm -rf {} +
	@find . -type d -name "*.eggs" -exec rm -rf {} +
	@find . -type d -name ".pytest_cache" -exec rm -rf {} +
	@find . -type d -name ".coverage" -exec rm -rf {} +
	@find . -type d -name ".mypy_cache" -exec rm -rf {} +
	@find . -type d -name ".hypothesis" -exec rm -rf {} +
	@find . -type d -name "htmlcov" -exec rm -rf {} +
	@find . -name "*.pyc" -delete
	@find . -name "*.pyo" -delete
	@find . -name "*.pyd" -delete
	@find . -name ".coverage" -delete
	@find . -name "coverage.xml" -delete
	@find . -name "*.log" -delete
	@rm -rf build/
	@rm -rf dist/
	@rm -rf .tox/
	@echo "✅ ¡Limpieza completada!"

# Objetivo para crear entorno limpio y configurado
clean-setup: clean setup
	@echo "🔄 ¡Entorno limpiado y configurado exitosamente!"

# Establecer menú como objetivo predeterminado
.DEFAULT_GOAL := menu