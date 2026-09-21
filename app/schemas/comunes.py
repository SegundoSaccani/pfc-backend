from app.schemas.base import CamelModel


class Ubicacion(CamelModel):
    latitud: float
    longitud: float
