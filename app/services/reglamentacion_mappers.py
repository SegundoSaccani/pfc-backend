from app.models import Regla, Reglamentacion
from app.schemas.reglamentacion import ReglaDetalle, ReglamentacionDetalle, ReglamentacionResumen
from app.services.relevamiento_mappers import especie_a_resumen


def regla_a_detalle(regla: Regla) -> ReglaDetalle:
    return ReglaDetalle(
        id=regla.id,
        especie=especie_a_resumen(regla.especie),
        talla_minima=regla.talla_min,
        talla_maxima=regla.talla_max,
        veda=regla.en_veda,
    )


def reglamentacion_a_resumen(reglamentacion: Reglamentacion) -> ReglamentacionResumen:
    return ReglamentacionResumen(
        id=reglamentacion.id,
        fecha_inicio=reglamentacion.fecha_inicio,
        fecha_fin=reglamentacion.fecha_fin,
    )


def reglamentacion_a_detalle(reglamentacion: Reglamentacion) -> ReglamentacionDetalle:
    return ReglamentacionDetalle(
        id=reglamentacion.id,
        fecha_inicio=reglamentacion.fecha_inicio,
        fecha_fin=reglamentacion.fecha_fin,
        reglas=[regla_a_detalle(r) for r in reglamentacion.reglas],
    )
