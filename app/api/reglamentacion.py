from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.auth import require_rol
from app.core.roles import Rol
from app.db.session import get_db
from app.schemas.reglamentacion import (
    ReglaCreate,
    ReglaDetalle,
    ReglaUpdate,
    ReglamentacionCreate,
    ReglamentacionDetalle,
    ReglamentacionResumen,
)
from app.services import reglamentaciones as service

router = APIRouter(prefix="/api", tags=["reglamentacion"])


@router.get("/reglamentacion", response_model=ReglamentacionDetalle)
def obtener_reglamentacion_vigente(
    fecha: date | None = Query(None),
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.FISCALIZADOR, Rol.USUARIO, Rol.ADMINISTRADOR)),
):
    return service.obtener_vigente(db, fecha)


@router.get("/reglamentaciones", response_model=list[ReglamentacionResumen])
def listar_reglamentaciones(
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.USUARIO, Rol.ADMINISTRADOR)),
):
    return service.listar_reglamentaciones(db)


@router.post("/reglamentaciones", response_model=ReglamentacionDetalle, status_code=201)
def crear_reglamentacion(
    payload: ReglamentacionCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    return service.crear_reglamentacion(db, payload)


@router.put("/reglamentaciones/{reglamentacion_id}", response_model=ReglamentacionDetalle)
def actualizar_reglamentacion(
    reglamentacion_id: int,
    payload: ReglamentacionCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    return service.actualizar_reglamentacion(db, reglamentacion_id, payload)


@router.delete("/reglamentaciones/{reglamentacion_id}", status_code=204)
def eliminar_reglamentacion(
    reglamentacion_id: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    service.eliminar_reglamentacion(db, reglamentacion_id)


@router.post(
    "/reglamentaciones/{reglamentacion_id}/reglas", response_model=ReglaDetalle, status_code=201
)
def crear_regla(
    reglamentacion_id: int,
    payload: ReglaCreate,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    return service.crear_regla(db, reglamentacion_id, payload)


@router.put("/reglas/{regla_id}", response_model=ReglaDetalle)
def actualizar_regla(
    regla_id: int,
    payload: ReglaUpdate,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    return service.actualizar_regla(db, regla_id, payload)


@router.delete("/reglas/{regla_id}", status_code=204)
def eliminar_regla(
    regla_id: int,
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(Rol.ADMINISTRADOR)),
):
    service.eliminar_regla(db, regla_id)
