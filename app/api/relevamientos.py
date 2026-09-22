from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.auth import require_rol
from app.core.roles import Rol
from app.db.session import get_db
from app.repositories.relevamientos import FiltrosRelevamiento
from app.schemas.relevamiento import (
    RelevamientoCreate,
    RelevamientoCreateResponse,
    RelevamientoDetalle,
    RelevamientoListResponse,
)
from app.services import relevamientos as service

router = APIRouter(prefix="/api", tags=["relevamientos"])


@router.post("/relevamientos", response_model=RelevamientoCreateResponse)
def crear_relevamiento(
    payload: RelevamientoCreate,
    response: Response,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.FISCALIZADOR, Rol.ADMINISTRADOR)),
):
    resultado = service.crear_relevamiento(db, payload)
    response.status_code = 201 if resultado.estado == "REGISTRADO" else 200
    return resultado


@router.get("/relevamientos", response_model=RelevamientoListResponse)
def listar_relevamientos(
    fechaDesde: date | None = Query(None),
    fechaHasta: date | None = Query(None),
    especie: str | None = Query(None),
    puntoDesembarco: str | None = Query(None),
    nroPescador: int | None = Query(None),
    page: int = Query(0, ge=0),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.USUARIO, Rol.ADMINISTRADOR)),
):
    filtros = FiltrosRelevamiento(
        fecha_desde=fechaDesde,
        fecha_hasta=fechaHasta,
        especie=especie,
        punto_desembarco=puntoDesembarco,
        nro_pescador=nroPescador,
    )
    return service.listar_relevamientos(db, filtros, page, size)


@router.get("/relevamientos/{relevamiento_id}", response_model=RelevamientoDetalle)
def obtener_relevamiento(
    relevamiento_id: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.USUARIO, Rol.ADMINISTRADOR)),
):
    return service.obtener_relevamiento_detalle(db, relevamiento_id)
