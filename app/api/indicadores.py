from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_rol
from app.core.roles import Rol
from app.db.session import get_db
from app.repositories.indicadores import FiltrosIndicador
from app.schemas.indicadores import (
    Agrupacion,
    CapturasPorEspecieResponse,
    CapturasPorPuntoResponse,
    EvolucionTemporalResponse,
)
from app.services import indicadores as service

router = APIRouter(prefix="/api/indicadores", tags=["indicadores"])

_ROLES_LECTURA = (Rol.USUARIO, Rol.ADMINISTRADOR)


def _filtros(
    fechaDesde: date | None, fechaHasta: date | None, especieId: int | None, puntoDesembarcoId: int | None
) -> FiltrosIndicador:
    return FiltrosIndicador(
        fecha_desde=fechaDesde,
        fecha_hasta=fechaHasta,
        especie_id=especieId,
        punto_desembarco_id=puntoDesembarcoId,
    )


@router.get("/capturas-por-especie", response_model=CapturasPorEspecieResponse)
def capturas_por_especie(
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especieId: int | None = Query(None),
    puntoDesembarcoId: int | None = Query(None),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_ROLES_LECTURA)),
):
    return service.capturas_por_especie(db, _filtros(fechaDesde, fechaHasta, especieId, puntoDesembarcoId))


@router.get("/capturas-por-punto", response_model=CapturasPorPuntoResponse)
def capturas_por_punto(
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especieId: int | None = Query(None),
    puntoDesembarcoId: int | None = Query(None),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_ROLES_LECTURA)),
):
    return service.capturas_por_punto(db, _filtros(fechaDesde, fechaHasta, especieId, puntoDesembarcoId))


@router.get("/evolucion-temporal", response_model=EvolucionTemporalResponse)
def evolucion_temporal(
    agrupacion: Agrupacion,
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especieId: int | None = Query(None),
    puntoDesembarcoId: int | None = Query(None),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_ROLES_LECTURA)),
):
    return service.evolucion_temporal(
        db, agrupacion, _filtros(fechaDesde, fechaHasta, especieId, puntoDesembarcoId)
    )
