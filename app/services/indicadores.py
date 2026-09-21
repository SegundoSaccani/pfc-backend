from sqlalchemy.orm import Session

from app.repositories import indicadores as repo
from app.repositories.indicadores import FiltrosIndicador
from app.schemas.indicadores import (
    Agrupacion,
    CapturaPorEspecieDesglose,
    CapturaPorEspecieItem,
    CapturaPorPuntoItem,
    CapturasPorEspecieResponse,
    CapturasPorPuntoResponse,
    EvolucionTemporalItem,
    EvolucionTemporalResponse,
)

_FORMATO_PERIODO = {"dia": "%Y-%m-%d", "mes": "%Y-%m", "anio": "%Y"}


def capturas_por_especie(session: Session, filtros: FiltrosIndicador) -> CapturasPorEspecieResponse:
    filas = repo.capturas_por_especie(session, filtros)
    datos = [
        CapturaPorEspecieItem(especie_id=especie_id, nombre_especie=nombre, cantidad=cantidad)
        for especie_id, nombre, cantidad in filas
    ]
    # excluidos siempre 0: fecha_hora es NOT NULL y se valida como ISO 8601 al ingresar el
    # relevamiento, así que no hay forma de tener una fecha inválida/incompleta en la base
    # (limitación documentada en PLAN.md).
    return CapturasPorEspecieResponse(datos=datos, excluidos=0)


def capturas_por_punto(session: Session, filtros: FiltrosIndicador) -> CapturasPorPuntoResponse:
    filas = repo.capturas_por_punto(session, filtros)

    desglose_por_punto: dict[int, list[CapturaPorEspecieDesglose]] = {}
    incluir_desglose = filtros.especie_id is None
    if incluir_desglose:
        for punto_id, especie_id, nombre_especie, cantidad in repo.capturas_por_punto_desglose_especie(
            session, filtros
        ):
            desglose_por_punto.setdefault(punto_id, []).append(
                CapturaPorEspecieDesglose(especie_id=especie_id, nombre_especie=nombre_especie, cantidad=cantidad)
            )

    datos = [
        CapturaPorPuntoItem(
            punto_desembarco_id=punto_id,
            nombre=nombre,
            cantidad=cantidad,
            por_especie=desglose_por_punto.get(punto_id, []) if incluir_desglose else None,
        )
        for punto_id, nombre, cantidad in filas
    ]
    return CapturasPorPuntoResponse(datos=datos, excluidos=0)


def evolucion_temporal(
    session: Session, agrupacion: Agrupacion, filtros: FiltrosIndicador
) -> EvolucionTemporalResponse:
    filas = repo.evolucion_temporal(session, agrupacion.value, filtros)
    formato = _FORMATO_PERIODO[agrupacion.value]
    datos = [
        EvolucionTemporalItem(periodo=periodo.strftime(formato), cantidad=cantidad)
        for periodo, cantidad in filas
    ]
    return EvolucionTemporalResponse(agrupacion=agrupacion, datos=datos, excluidos=0)
