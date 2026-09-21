from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from app.schemas.comunes import Ubicacion
from app.services.geo import geografia_a_ubicacion, ubicacion_a_geografia


def test_ubicacion_a_geografia_usa_orden_longitud_latitud():
    wkt = ubicacion_a_geografia(Ubicacion(latitud=-31.633, longitud=-60.699))
    assert wkt.desc == "POINT(-60.699 -31.633)"
    assert wkt.srid == 4326


def test_ubicacion_a_geografia_none_es_none():
    assert ubicacion_a_geografia(None) is None


def test_geografia_a_ubicacion_round_trip():
    punto_wkb = from_shape(Point(-60.699, -31.633), srid=4326)

    ubicacion = geografia_a_ubicacion(punto_wkb)

    assert ubicacion.latitud == -31.633
    assert ubicacion.longitud == -60.699


def test_geografia_a_ubicacion_none_es_none():
    assert geografia_a_ubicacion(None) is None
