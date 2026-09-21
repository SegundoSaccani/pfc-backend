from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import Regla, Reglamentacion

# Sentinel para tratar fecha_fin NULL ("sin fin") como "infinito" al comparar rangos.
FECHA_MAXIMA = date(9999, 12, 31)


def existe_solapamiento(
    session: Session, fecha_inicio: date, fecha_fin: date | None, excluir_id: int | None = None
) -> bool:
    fin_nuevo = fecha_fin or FECHA_MAXIMA
    condiciones = [
        Reglamentacion.fecha_inicio <= fin_nuevo,
        or_(Reglamentacion.fecha_fin.is_(None), Reglamentacion.fecha_fin >= fecha_inicio),
    ]
    if excluir_id is not None:
        condiciones.append(Reglamentacion.id != excluir_id)
    return session.scalar(select(Reglamentacion.id).where(*condiciones)) is not None


def obtener_vigente(session: Session, fecha: date) -> Reglamentacion | None:
    stmt = (
        select(Reglamentacion)
        .where(
            Reglamentacion.fecha_inicio <= fecha,
            or_(Reglamentacion.fecha_fin.is_(None), Reglamentacion.fecha_fin >= fecha),
        )
        .options(selectinload(Reglamentacion.reglas).joinedload(Regla.especie))
    )
    return session.execute(stmt).unique().scalar_one_or_none()


def listar_historico(session: Session) -> list[Reglamentacion]:
    return list(
        session.scalars(select(Reglamentacion).order_by(Reglamentacion.fecha_inicio.desc())).all()
    )


def obtener_por_id(session: Session, reglamentacion_id: int, con_reglas: bool = False) -> Reglamentacion | None:
    stmt = select(Reglamentacion).where(Reglamentacion.id == reglamentacion_id)
    if con_reglas:
        stmt = stmt.options(selectinload(Reglamentacion.reglas).joinedload(Regla.especie))
        return session.execute(stmt).unique().scalar_one_or_none()
    return session.scalar(stmt)


def crear(session: Session, fecha_inicio: date, fecha_fin: date | None) -> Reglamentacion:
    reglamentacion = Reglamentacion(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)
    session.add(reglamentacion)
    session.flush()
    return reglamentacion


def eliminar(session: Session, reglamentacion: Reglamentacion) -> None:
    session.delete(reglamentacion)


def obtener_regla(session: Session, regla_id: int) -> Regla | None:
    return session.execute(
        select(Regla).where(Regla.id == regla_id).options(joinedload(Regla.especie))
    ).scalar_one_or_none()


def crear_regla(
    session: Session, reglamentacion_id: int, especie_id: int, en_veda: bool, talla_min: float, talla_max: float
) -> Regla:
    regla = Regla(
        id_reglamentacion=reglamentacion_id,
        id_especie=especie_id,
        en_veda=en_veda,
        talla_min=talla_min,
        talla_max=talla_max,
    )
    session.add(regla)
    session.flush()
    return regla


def eliminar_regla(session: Session, regla: Regla) -> None:
    session.delete(regla)
