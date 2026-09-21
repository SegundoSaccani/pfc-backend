from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import catalogos, export, health, indicadores, reglamentacion, relevamientos
from app.core.errors import ApiError

_CODIGO_POR_STATUS = {
    401: "NO_AUTORIZADO",
    403: "PROHIBIDO",
    404: "RECURSO_NO_ENCONTRADO",
    409: "CONFLICTO",
    422: "ERROR_VALIDACION",
}


def _error_response(status_code: int, codigo: str, mensaje: str, detalles: list | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"codigo": codigo, "mensaje": mensaje, "detalles": detalles or []}},
    )


def create_app() -> FastAPI:
    app = FastAPI(title="API Relevamiento Pesca Artesanal")

    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return _error_response(exc.status_code, exc.codigo, exc.mensaje, exc.detalles)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        codigo = _CODIGO_POR_STATUS.get(exc.status_code, "ERROR_INTERNO" if exc.status_code >= 500 else "ERROR_SOLICITUD")
        mensaje = exc.detail if isinstance(exc.detail, str) else "Error en la solicitud."
        return _error_response(exc.status_code, codigo, mensaje)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _error_response(
            422,
            "ERROR_VALIDACION",
            "Error de validación en la solicitud.",
            jsonable_encoder(exc.errors()),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return _error_response(500, "ERROR_INTERNO", "Error interno del servidor.")

    app.include_router(health.router)
    # export.router va antes que relevamientos.router: "/api/relevamientos/export" tiene que
    # matchear antes que "/api/relevamientos/{relevamiento_id}" (si no, Starlette intenta parsear
    # "export" como id y devuelve 422 en vez de exportar).
    app.include_router(export.router)
    app.include_router(relevamientos.router)
    app.include_router(catalogos.router)
    app.include_router(reglamentacion.router)
    app.include_router(indicadores.router)

    return app


app = create_app()
