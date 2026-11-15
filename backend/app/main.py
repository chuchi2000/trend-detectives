"""Punto de entrada de la API del Atlas Ambiental de México.

Ejecutar en desarrollo (desde la carpeta backend/):

    uvicorn app.main:app --reload --port 8000

Documentación interactiva: http://localhost:8000/docs
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import analysis, catalog, export, layers, regions
from app.core.config import get_settings
from app.core.errors import AtlasError
from app.core.i18n import reset_lang, set_lang, tr
from app.core.logging import configure_logging
from app.services.atlas import VERSION

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("atlas.api")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Atlas API %s iniciada en modo %s", VERSION, settings.data_mode.upper())
    if settings.data_mode == "demo":
        logger.warning(
            "Modo DEMO: las respuestas contienen datos SIMULADOS, no mediciones de NASA."
        )
    yield


app = FastAPI(
    lifespan=lifespan,
    title="Atlas Ambiental de México — API",
    version=VERSION,
    description=(
        "API REST del Atlas Ambiental de México. Sirve variables, capas, metadatos, "
        "series de tiempo y estadísticas de productos satelitales de NASA. "
        f"Modo de datos actual: **{settings.data_mode.upper()}**."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(AtlasError)
async def atlas_error_handler(request: Request, exc: AtlasError) -> JSONResponse:
    logger.info("%s %s -> %s (%s)", request.method, request.url.path, exc.status_code, exc.code)
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error no controlado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "error_interno",
                "message": tr(
                    "Ocurrió un error inesperado. Revisa los logs del backend.",
                    "An unexpected error occurred. Check the backend logs.",
                ),
            }
        },
    )


class LanguageMiddleware:
    """Idioma de la respuesta: ?lang=en|es o, si no viene, el encabezado Accept-Language.

    Middleware ASGI puro (no BaseHTTPMiddleware) para que la ContextVar del idioma
    llegue a las rutas síncronas que FastAPI ejecuta en su grupo de hilos.
    """

    def __init__(self, app_: object) -> None:
        self.app = app_

    async def __call__(self, scope, receive, send):  # noqa: ANN001
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        from urllib.parse import parse_qs

        query = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        value = (query.get("lang") or [None])[0]
        if value is None:
            headers = dict(scope.get("headers") or [])
            value = headers.get(b"accept-language", b"").decode("latin-1") or None
        token = set_lang(value)
        try:
            await self.app(scope, receive, send)
        finally:
            reset_lang(token)


app.add_middleware(LanguageMiddleware)

for module in (catalog, layers, analysis, regions, export):
    app.include_router(module.router, prefix="/api")
