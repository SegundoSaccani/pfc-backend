from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import Conflicto, ErrorValidacion, RecursoNoEncontrado
from app.core.tz import hoy
from app.repositories import reglamentaciones as repo
from app.repositories.relevamientos import obtener_especie_por_nombre
from app.schemas.reglamentacion import (
    ReglaCreate,
    ReglaDetalle,
    ReglaUpdate,
    ReglamentacionCreate,
    ReglamentacionDetalle,
    ReglamentacionResumen,
)
from app.services.reglamentacion_mappers import (
    reglamentacion_a_detalle,
    reglamentacion_a_resumen,
    regla_a_detalle,
)

TALLA_MIN_EN_VEDA = 0.0
TALLA_MAX_EN_VEDA = 9999.0


def _validar_rango_fechas(fecha_inicio: date, fecha_fin: date | None) -> None:
    if fecha_fin is not None and fecha_fin < fecha_inicio:
        raise ErrorValidacion(
            "fechaFin no puede ser anterior a fechaInicio.",
            [{"campo": "fechaFin", "mensaje": "Debe ser posterior o igual a fechaInicio."}],
        )


def _validar_no_solapa(session: Session, fecha_inicio: date, fecha_fin: date | None, excluir_id: int | None = None) -> None:
    if repo.existe_solapamiento(session, fecha_inicio, fecha_fin, excluir_id):
        raise Conflicto("La reglamentación se solapa en el tiempo con una reglamentación existente.")


def crear_reglamentacion(session: Session, payload: ReglamentacionCreate) -> ReglamentacionDetalle:
    _validar_rango_fechas(payload.fecha_inicio, payload.fecha_fin)
    _validar_no_solapa(session, payload.fecha_inicio, payload.fecha_fin)

    reglamentacion = repo.crear(session, payload.fecha_inicio, payload.fecha_fin)
    session.commit()
    return reglamentacion_a_detalle(reglamentacion)


def actualizar_reglamentacion(
    session: Session, reglamentacion_id: int, payload: ReglamentacionCreate
) -> ReglamentacionDetalle:
    reglamentacion = repo.obtener_por_id(session, reglamentacion_id, con_reglas=True)
    if reglamentacion is None:
        raise RecursoNoEncontrado(f"No existe la reglamentación {reglamentacion_id}.")

    _validar_rango_fechas(payload.fecha_inicio, payload.fecha_fin)
    _validar_no_solapa(session, payload.fecha_inicio, payload.fecha_fin, excluir_id=reglamentacion_id)

    reglamentacion.fecha_inicio = payload.fecha_inicio
    reglamentacion.fecha_fin = payload.fecha_fin
    session.commit()
    return reglamentacion_a_detalle(reglamentacion)


def eliminar_reglamentacion(session: Session, reglamentacion_id: int) -> None:
    reglamentacion = repo.obtener_por_id(session, reglamentacion_id)
    if reglamentacion is None:
        raise RecursoNoEncontrado(f"No existe la reglamentación {reglamentacion_id}.")
    repo.eliminar(session, reglamentacion)
    session.commit()


def listar_reglamentaciones(session: Session) -> list[ReglamentacionResumen]:
    return [reglamentacion_a_resumen(r) for r in repo.listar_historico(session)]


def obtener_vigente(session: Session, fecha: date | None) -> ReglamentacionDetalle:
    fecha_efectiva = fecha or hoy()
    reglamentacion = repo.obtener_vigente(session, fecha_efectiva)
    if reglamentacion is None:
        raise RecursoNoEncontrado(
            f"No hay reglamentación vigente para la fecha {fecha_efectiva.isoformat()}."
        )
    return reglamentacion_a_detalle(reglamentacion)


def _tallas_segun_convencion_veda(
    veda: bool, talla_minima: float | None, talla_maxima: float | None
) -> tuple[float, float]:
    if veda:
        return TALLA_MIN_EN_VEDA, TALLA_MAX_EN_VEDA
    if talla_minima is None or talla_maxima is None:
        raise ErrorValidacion(
            "tallaMinima y tallaMaxima son obligatorias cuando la especie no está en veda.",
            [
                {"campo": "tallaMinima", "mensaje": "Obligatoria si veda=false."},
                {"campo": "tallaMaxima", "mensaje": "Obligatoria si veda=false."},
            ],
        )
    return talla_minima, talla_maxima


def crear_regla(session: Session, reglamentacion_id: int, payload: ReglaCreate) -> ReglaDetalle:
    if repo.obtener_por_id(session, reglamentacion_id) is None:
        raise RecursoNoEncontrado(f"No existe la reglamentación {reglamentacion_id}.")

    especie = obtener_especie_por_nombre(session, payload.especie)
    if especie is None:
        raise ErrorValidacion(
            f"No existe la especie '{payload.especie}'.",
            [{"campo": "especie", "mensaje": "La especie no existe."}],
        )

    talla_min, talla_max = _tallas_segun_convencion_veda(
        payload.veda, payload.talla_minima, payload.talla_maxima
    )

    try:
        regla = repo.crear_regla(
            session, reglamentacion_id, especie.id, payload.veda, talla_min, talla_max
        )
        session.commit()
    except IntegrityError:
        session.rollback()
        raise Conflicto("Ya existe una regla para esta especie en esta reglamentación.")

    return regla_a_detalle(regla)


def actualizar_regla(session: Session, regla_id: int, payload: ReglaUpdate) -> ReglaDetalle:
    regla = repo.obtener_regla(session, regla_id)
    if regla is None:
        raise RecursoNoEncontrado(f"No existe la regla {regla_id}.")

    especie = None
    if payload.especie is not None:
        especie = obtener_especie_por_nombre(session, payload.especie)
        if especie is None:
            raise ErrorValidacion(
                f"No existe la especie '{payload.especie}'.",
                [{"campo": "especie", "mensaje": "La especie no existe."}],
            )

    talla_min, talla_max = _tallas_segun_convencion_veda(
        payload.veda, payload.talla_minima, payload.talla_maxima
    )

    regla.en_veda = payload.veda
    regla.talla_min = talla_min
    regla.talla_max = talla_max
    if especie is not None:
        regla.id_especie = especie.id

    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise Conflicto("Ya existe una regla para esta especie en esta reglamentación.")

    return regla_a_detalle(regla)


def eliminar_regla(session: Session, regla_id: int) -> None:
    regla = repo.obtener_regla(session, regla_id)
    if regla is None:
        raise RecursoNoEncontrado(f"No existe la regla {regla_id}.")
    repo.eliminar_regla(session, regla)
    session.commit()
