class ApiError(Exception):
    """Excepción base para errores de negocio con el formato de error único de la API."""

    def __init__(self, status_code: int, codigo: str, mensaje: str, detalles: list | None = None):
        self.status_code = status_code
        self.codigo = codigo
        self.mensaje = mensaje
        self.detalles = detalles or []
        super().__init__(mensaje)


class RecursoNoEncontrado(ApiError):
    def __init__(self, mensaje: str, detalles: list | None = None):
        super().__init__(404, "RECURSO_NO_ENCONTRADO", mensaje, detalles)


class ErrorValidacion(ApiError):
    def __init__(self, mensaje: str, detalles: list | None = None):
        super().__init__(422, "ERROR_VALIDACION", mensaje, detalles)


class Conflicto(ApiError):
    def __init__(self, mensaje: str, detalles: list | None = None):
        super().__init__(409, "CONFLICTO", mensaje, detalles)
