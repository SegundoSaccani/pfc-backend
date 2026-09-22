from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import EspeciePescado, Fiscalizador, Pescador, PescadoIndividuo, PuntoDesembarco, Relevamiento

_CONSTRAINT_DUPLICADOS = "relevamiento_fecha_hora_id_pescador_id_fiscalizador_unique"


def obtener_especie_por_nombre(session: Session, nombre_especie: str) -> EspeciePescado | None:
    return session.scalar(select(EspeciePescado).where(EspeciePescado.nombre_especie == nombre_especie))


def obtener_pescador_por_nro(session: Session, nro_pescador: int) -> Pescador | None:
    return session.scalar(select(Pescador).where(Pescador.nro_pescador == nro_pescador))


def obtener_fiscalizador_por_nombre_user(session: Session, nombre_user: str) -> Fiscalizador | None:
    return session.scalar(select(Fiscalizador).where(Fiscalizador.nombre_user == nombre_user))


def obtener_punto_desembarco_por_nombre(session: Session, nombre: str) -> PuntoDesembarco | None:
    return session.scalar(select(PuntoDesembarco).where(PuntoDesembarco.nombre == nombre))


def insertar_relevamiento_o_duplicado(session: Session, valores: dict) -> tuple[int, bool]:
    """Devuelve (id, es_nuevo). `es_nuevo=False` significa que ya existía (mismo fecha_hora +
    pescador + fiscalizador) y se devuelve el id existente sin tocar sus individuos."""
    stmt = (
        pg_insert(Relevamiento)
        .values(**valores)
        .on_conflict_do_nothing(constraint=_CONSTRAINT_DUPLICADOS)
        .returning(Relevamiento.id)
    )
    fila = session.execute(stmt).first()
    if fila is not None:
        return fila[0], True

    id_existente = session.scalar(
        select(Relevamiento.id).where(
            Relevamiento.fecha_hora == valores["fecha_hora"],
            Relevamiento.id_pescador == valores["id_pescador"],
            Relevamiento.id_fiscalizador == valores["id_fiscalizador"],
        )
    )
    return id_existente, False


def insertar_individuos(session: Session, id_relevamiento: int, individuos: list[dict]) -> None:
    if not individuos:
        return
    session.execute(
        PescadoIndividuo.__table__.insert(),
        [{**i, "id_relevamiento": id_relevamiento} for i in individuos],
    )


def obtener_detalle(session: Session, relevamiento_id: int) -> Relevamiento | None:
    stmt = (
        select(Relevamiento)
        .where(Relevamiento.id == relevamiento_id)
        .options(
            joinedload(Relevamiento.punto_desembarco),
            joinedload(Relevamiento.fiscalizador),
            joinedload(Relevamiento.pescador),
            selectinload(Relevamiento.individuos).joinedload(PescadoIndividuo.especie),
        )
    )
    return session.execute(stmt).unique().scalar_one_or_none()


@dataclass
class FiltrosRelevamiento:
    """Filtros expuestos a clientes externos (web): siempre por clave de negocio (uniques), nunca
    por el id interno de Pescador/Fiscalizador/Punto_desembarco/Especie_Pescado (CLAUDE.md)."""

    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    especie: str | None = None
    punto_desembarco: str | None = None
    nro_pescador: int | None = None

    def condiciones(self) -> list:
        condiciones = []
        if self.fecha_desde is not None:
            condiciones.append(Relevamiento.fecha_hora >= self.fecha_desde)
        if self.fecha_hasta is not None:
            condiciones.append(Relevamiento.fecha_hora < self.fecha_hasta_exclusiva())
        if self.punto_desembarco is not None:
            condiciones.append(
                Relevamiento.id_punto_desembarco.in_(
                    select(PuntoDesembarco.id).where(PuntoDesembarco.nombre == self.punto_desembarco)
                )
            )
        if self.nro_pescador is not None:
            condiciones.append(
                Relevamiento.id_pescador.in_(
                    select(Pescador.id).where(Pescador.nro_pescador == self.nro_pescador)
                )
            )
        if self.especie is not None:
            condiciones.append(
                select(PescadoIndividuo.id)
                .join(EspeciePescado, PescadoIndividuo.id_especie == EspeciePescado.id)
                .where(
                    PescadoIndividuo.id_relevamiento == Relevamiento.id,
                    EspeciePescado.nombre_especie == self.especie,
                )
                .exists()
            )
        return condiciones

    def fecha_hasta_exclusiva(self) -> datetime:
        # fechaHasta es una fecha (sin hora): incluye todo ese día.
        return datetime.combine(self.fecha_hasta, datetime.min.time()) + timedelta(days=1)


def _conteos_individuos(session: Session, ids: list[int]) -> dict[int, int]:
    if not ids:
        return {}
    filas = session.execute(
        select(PescadoIndividuo.id_relevamiento, func.count())
        .where(PescadoIndividuo.id_relevamiento.in_(ids))
        .group_by(PescadoIndividuo.id_relevamiento)
    ).all()
    return {id_relevamiento: cantidad for id_relevamiento, cantidad in filas}


def listar(
    session: Session, filtros: FiltrosRelevamiento, page: int, size: int
) -> tuple[list[Relevamiento], dict[int, int], int]:
    condiciones = filtros.condiciones()

    total = session.scalar(
        select(func.count()).select_from(select(Relevamiento.id).where(*condiciones).subquery())
    )

    stmt = (
        select(Relevamiento)
        .where(*condiciones)
        .options(joinedload(Relevamiento.punto_desembarco), joinedload(Relevamiento.fiscalizador))
        .order_by(Relevamiento.fecha_hora.desc(), Relevamiento.id.desc())
        .offset(page * size)
        .limit(size)
    )
    relevamientos = session.execute(stmt).unique().scalars().all()
    conteos = _conteos_individuos(session, [r.id for r in relevamientos])

    return list(relevamientos), conteos, total or 0


def listar_para_exportar(
    session: Session, filtros: FiltrosRelevamiento
) -> tuple[list[Relevamiento], dict[int, int]]:
    """Igual que `listar`, sin paginar: la exportación CSV vuelca todo lo que matchea los filtros."""
    stmt = (
        select(Relevamiento)
        .where(*filtros.condiciones())
        .options(joinedload(Relevamiento.punto_desembarco), joinedload(Relevamiento.fiscalizador))
        .order_by(Relevamiento.fecha_hora.desc(), Relevamiento.id.desc())
    )
    relevamientos = session.execute(stmt).unique().scalars().all()
    conteos = _conteos_individuos(session, [r.id for r in relevamientos])
    return list(relevamientos), conteos
