from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.auth import require_rol
from app.core.roles import Rol
from app.db.session import get_db
from app.repositories.indicadores import FiltrosIndicador
from app.repositories.relevamientos import FiltrosRelevamiento
from app.schemas.indicadores import Agrupacion, IndicadorExportable
from app.services import export as service

router = APIRouter(prefix="/api", tags=["export"])

# Exportación es de solo lectura (PLAN.md sección 8.4 del prompt): mismos roles que pueden leer.
_ROLES_EXPORT = (Rol.USUARIO, Rol.ADMINISTRADOR)


def _streaming_csv(filas, nombre_archivo: str) -> StreamingResponse:
    return StreamingResponse(
        filas,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


@router.get("/relevamientos/export")
def exportar_relevamientos(
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especieId: int | None = Query(None),
    puntoDesembarcoId: int | None = Query(None),
    pescadorId: int | None = Query(None),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_ROLES_EXPORT)),
) -> StreamingResponse:
    filtros = FiltrosRelevamiento(
        fecha_desde=fechaDesde,
        fecha_hasta=fechaHasta,
        especie_id=especieId,
        punto_desembarco_id=puntoDesembarcoId,
        pescador_id=pescadorId,
    )
    filas, nombre_archivo = service.exportar_relevamientos(db, filtros)
    return _streaming_csv(filas, nombre_archivo)


@router.get("/indicadores/{indicador}/export")
def exportar_indicador(
    indicador: IndicadorExportable,
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especieId: int | None = Query(None),
    puntoDesembarcoId: int | None = Query(None),
    agrupacion: Agrupacion = Query(Agrupacion.MES),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_ROLES_EXPORT)),
) -> StreamingResponse:
    filtros = FiltrosIndicador(
        fecha_desde=fechaDesde,
        fecha_hasta=fechaHasta,
        especie_id=especieId,
        punto_desembarco_id=puntoDesembarcoId,
    )
    filas, nombre_archivo = service.exportar_indicador(db, indicador, filtros, agrupacion)
    return _streaming_csv(filas, nombre_archivo)
