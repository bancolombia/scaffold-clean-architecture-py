from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import logging
from typing import Callable

from src.domain.usecase.health_check import HealthCheckUseCase


class RequestMiddleware:
    """Middleware para procesar solicitudes HTTP"""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    async def __call__(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Log request
        self.logger.info(f"Request started: {request.method} {request.url}")

        response = None
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            self.logger.error(f"Request failed: {str(e)}")
            return JSONResponse(
                status_code=500, content={"message": "Internal server error"}
            )
        finally:
            process_time = time.time() - start_time
            status_code = response.status_code if response else 500
            self.logger.info(
                f"Request completed: {request.method} {request.url} "
                f"status_code={status_code} duration={process_time:.3f}s"
            )


class FastAPIEntrypoint:
    """
    Punto de entrada para la API REST usando FastAPI
    """

    def __init__(
        self, health_check_use_case: HealthCheckUseCase, logger: logging.Logger
    ):
        self.app = FastAPI(
            title="Clean Architecture Service",
            description="Microservicio basado en Clean Architecture",
            version="1.0.0",
        )
        self.health_check_use_case = health_check_use_case
        self.logger = logger

        # Configurar CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Middleware para logging y métricas
        self.app.middleware("http")(RequestMiddleware(logger))

        # Registrar rutas
        self._register_routes()

    def _register_routes(self):
        """Registrar todas las rutas de la API"""

        @self.app.get("/health", tags=["Health"])
        async def health_check():
            """
            Comprueba el estado de salud del servicio
            """
            try:
                self.logger.info("Health check endpoint called")
                # Capturar el resultado en una variable para poder registrarlo
                result = self.health_check_use_case.execute()
                self.logger.info(f"Health check result: {result}")
                return result
            except Exception as e:
                # Loguear el error con la traza completa
                import traceback

                error_trace = traceback.format_exc()
                self.logger.error(f"Error in health check: {str(e)}\n{error_trace}")
                raise HTTPException(
                    status_code=500, detail=f"Error checking health status: {str(e)}"
                )
