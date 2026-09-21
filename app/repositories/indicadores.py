from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import Select, and_, func, literal, select, text
from sqlalchemy.orm import Session

from app.core.tz import ZONA_HORARIA
from app.models import EspeciePescado, PescadoIndividuo, PuntoDesembarco, Relevamiento

_ZONA_PG = str(ZONA_HORARIA.key)
UNIDAD_SQL = {"dia": "day", "mes": "month", "anio": "year"}


@dataclass
class FiltrosIndicador:
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    especie_id: int | None = None
    punto_desembarco_id: int | None = None

    def fecha_hasta_exclusiva(self) -> datetime:
        return datetime.combine(self.fecha_hasta, datetime.min.time()) + timedelta(days=1)

    def condiciones_fecha(self) -> list:
        condiciones = []
        if self.fecha_desde is not None:
            condiciones.append(Relevamiento.fecha_hora >= self.fecha_desde)
        if self.fecha_hasta is not None:
            condiciones.append(Relevamiento.fecha_hora < self.fecha_hasta_exclusiva())
        return condiciones

    def condiciones_relevamiento(self) -> list:
        condiciones = self.condiciones_fecha()
        if self.punto_desembarco_id is not None:
            condiciones.append(Relevamiento.id_punto_desembarco == self.punto_desembarco_id)
        return condiciones

    def condiciones(self) -> list:
        condiciones = self.condiciones_relevamiento()
        if self.especie_id is not None:
            condiciones.append(PescadoIndividuo.id_especie == self.especie_id)
        return condiciones


def _construir_capturas_por_especie(filtros: FiltrosIndicador) -> Select:
    return (
        select(EspeciePescado.id, EspeciePescado.nombre_especie, func.count(PescadoIndividuo.id))
        .select_from(PescadoIndividuo)
        .join(Relevamiento, PescadoIndividuo.id_relevamiento == Relevamiento.id)
        .join(EspeciePescado, PescadoIndividuo.id_especie == EspeciePescado.id)
        .where(*filtros.condiciones())
        .group_by(EspeciePescado.id, EspeciePescado.nombre_especie)
        .order_by(EspeciePescado.nombre_especie)
    )


def capturas_por_especie(session: Session, filtros: FiltrosIndicador):
    return session.execute(_construir_capturas_por_especie(filtros)).all()


def _construir_capturas_por_punto(filtros: FiltrosIndicador) -> Select:
    # Los filtros de fecha van en el ON del LEFT JOIN (para que los puntos sin capturas en el
    # período sigan apareciendo con cantidad 0). puntoDesembarcoId, en cambio, restringe qué
    # puntos se devuelven -> va en el WHERE, no en el ON (si no, listaría igual todos los puntos).
    condiciones_join_relevamiento = [PuntoDesembarco.id == Relevamiento.id_punto_desembarco]
    condiciones_join_relevamiento.extend(filtros.condiciones_fecha())

    condiciones_join_individuo = [PescadoIndividuo.id_relevamiento == Relevamiento.id]
    if filtros.especie_id is not None:
        condiciones_join_individuo.append(PescadoIndividuo.id_especie == filtros.especie_id)

    stmt = (
        select(PuntoDesembarco.id, PuntoDesembarco.nombre, func.count(PescadoIndividuo.id))
        .select_from(PuntoDesembarco)
        .outerjoin(Relevamiento, and_(*condiciones_join_relevamiento))
        .outerjoin(PescadoIndividuo, and_(*condiciones_join_individuo))
        .group_by(PuntoDesembarco.id, PuntoDesembarco.nombre, PuntoDesembarco.numero_orden)
        .order_by(PuntoDesembarco.numero_orden)
    )
    if filtros.punto_desembarco_id is not None:
        stmt = stmt.where(PuntoDesembarco.id == filtros.punto_desembarco_id)
    return stmt


def capturas_por_punto(session: Session, filtros: FiltrosIndicador):
    return session.execute(_construir_capturas_por_punto(filtros)).all()


def _construir_capturas_por_punto_desglose_especie(filtros: FiltrosIndicador) -> Select:
    return (
        select(
            PuntoDesembarco.id,
            EspeciePescado.id,
            EspeciePescado.nombre_especie,
            func.count(PescadoIndividuo.id),
        )
        .select_from(PuntoDesembarco)
        .join(Relevamiento, PuntoDesembarco.id == Relevamiento.id_punto_desembarco)
        .join(PescadoIndividuo, PescadoIndividuo.id_relevamiento == Relevamiento.id)
        .join(EspeciePescado, PescadoIndividuo.id_especie == EspeciePescado.id)
        .where(*filtros.condiciones_relevamiento())
        .group_by(PuntoDesembarco.id, EspeciePescado.id, EspeciePescado.nombre_especie)
    )


def capturas_por_punto_desglose_especie(session: Session, filtros: FiltrosIndicador):
    return session.execute(_construir_capturas_por_punto_desglose_especie(filtros)).all()


def _construir_evolucion_temporal(
    filtros: FiltrosIndicador, unidad_pg: str, rango_inicio: datetime, rango_fin: datetime
) -> Select:
    fecha_local = func.timezone(_ZONA_PG, Relevamiento.fecha_hora)
    periodo_expr = func.date_trunc(unidad_pg, fecha_local)

    inicio_truncado = func.date_trunc(unidad_pg, literal(rango_inicio))
    fin_truncado = func.date_trunc(unidad_pg, literal(rango_fin))

    periodos = func.generate_series(
        inicio_truncado, fin_truncado, text(f"interval '1 {unidad_pg}'")
    ).table_valued("periodo")

    capturas = (
        select(periodo_expr.label("periodo"), func.count(PescadoIndividuo.id).label("cantidad"))
        .select_from(PescadoIndividuo)
        .join(Relevamiento, PescadoIndividuo.id_relevamiento == Relevamiento.id)
        .where(*filtros.condiciones())
        .group_by(periodo_expr)
        .subquery()
    )

    return (
        select(periodos.c.periodo, func.coalesce(capturas.c.cantidad, 0))
        .select_from(periodos)
        .outerjoin(capturas, capturas.c.periodo == periodos.c.periodo)
        .order_by(periodos.c.periodo)
    )


def _rango_evolucion_temporal(session: Session, filtros: FiltrosIndicador) -> tuple[datetime, datetime] | None:
    if filtros.fecha_desde is not None and filtros.fecha_hasta is not None:
        return (
            datetime.combine(filtros.fecha_desde, datetime.min.time()),
            datetime.combine(filtros.fecha_hasta, datetime.min.time()),
        )

    fecha_local = func.timezone(_ZONA_PG, Relevamiento.fecha_hora)
    limites = session.execute(
        select(func.min(fecha_local), func.max(fecha_local))
        .select_from(PescadoIndividuo)
        .join(Relevamiento, PescadoIndividuo.id_relevamiento == Relevamiento.id)
        .where(*filtros.condiciones())
    ).one()
    if limites[0] is None:
        return None
    return limites[0], limites[1]


def evolucion_temporal(session: Session, agrupacion: str, filtros: FiltrosIndicador):
    unidad_pg = UNIDAD_SQL[agrupacion]
    rango = _rango_evolucion_temporal(session, filtros)
    if rango is None:
        return []
    stmt = _construir_evolucion_temporal(filtros, unidad_pg, rango[0], rango[1])
    return session.execute(stmt).all()
