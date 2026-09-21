from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.auth import require_rol
from app.core.roles import Rol
from app.db.session import get_db
from app.models import EspeciePescado, PuntoDesembarco
from app.schemas.relevamiento import EspecieResumen, PuntoDesembarcoResumen

router = APIRouter(prefix="/api", tags=["catalogos"])

_CUALQUIER_ROL = (Rol.FISCALIZADOR, Rol.USUARIO, Rol.ADMINISTRADOR)


@router.get("/especies", response_model=list[EspecieResumen])
def listar_especies(
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_CUALQUIER_ROL)),
):
    especies = db.scalars(select(EspeciePescado).order_by(EspeciePescado.nombre_especie)).all()
    return [EspecieResumen(id=e.id, nombre=e.nombre_especie) for e in especies]


@router.get("/puntos-desembarco", response_model=list[PuntoDesembarcoResumen])
def listar_puntos_desembarco(
    db: Session = Depends(get_db),
    _usuario=Depends(require_rol(*_CUALQUIER_ROL)),
):
    # Ordenado por numero_orden (PLAN.md sección 5.2 del prompt). Sin `ubicacion`: la tabla no
    # tiene esa columna (divergencia documentada respecto al ejemplo de api_spec.txt).
    puntos = db.scalars(select(PuntoDesembarco).order_by(PuntoDesembarco.numero_orden)).all()
    return [PuntoDesembarcoResumen(id=p.id, nombre=p.nombre) for p in puntos]
