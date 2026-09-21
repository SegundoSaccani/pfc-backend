"""Autorización — STUB TEMPORAL.

No hay autenticación real todavía (sin JWT, sin login, sin tablas de usuarios: ver PLAN.md
sección 6). `get_current_user()` devuelve un usuario ficticio cuyo rol sale de la env var
DEFAULT_ROL, solo para poder desarrollar y probar `require_rol` con los roles definitivos desde
ahora. El día que exista auth real, este es el único archivo que hay que reemplazar: los routers
ya van a estar usando `require_rol(...)` con los roles correctos.
"""

from fastapi import Depends, HTTPException, status
from pydantic import BaseModel

from app.core.config import settings
from app.core.roles import Rol


class UsuarioActual(BaseModel):
    id: int
    rol: Rol


def get_current_user() -> UsuarioActual:
    """STUB TEMPORAL. Reemplazar por la resolución real del usuario a partir del token."""
    return UsuarioActual(id=0, rol=settings.default_rol)


def require_rol(*roles: Rol):
    def _dependency(usuario: UsuarioActual = Depends(get_current_user)) -> UsuarioActual:
        if usuario.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permiso para realizar esta acción.",
            )
        return usuario

    return _dependency
