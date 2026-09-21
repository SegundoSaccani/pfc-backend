from geoalchemy2.elements import WKBElement, WKTElement
from geoalchemy2.shape import to_shape

from app.schemas.comunes import Ubicacion


def ubicacion_a_geografia(ubicacion: Ubicacion | None) -> WKTElement | None:
    if ubicacion is None:
        return None
    return WKTElement(f"POINT({ubicacion.longitud} {ubicacion.latitud})", srid=4326)


def geografia_a_ubicacion(geografia: WKBElement | None) -> Ubicacion | None:
    if geografia is None:
        return None
    punto = to_shape(geografia)
    return Ubicacion(latitud=punto.y, longitud=punto.x)
