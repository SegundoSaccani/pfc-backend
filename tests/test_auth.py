import pytest
from fastapi import HTTPException

from app.core.auth import UsuarioActual, get_current_user, require_rol
from app.core.config import settings
from app.core.roles import Rol


def test_get_current_user_usa_rol_de_la_config(monkeypatch):
    monkeypatch.setattr(settings, "default_rol", Rol.FISCALIZADOR)
    usuario = get_current_user()
    assert usuario.rol == Rol.FISCALIZADOR


def test_require_rol_permite_rol_autorizado():
    dependencia = require_rol(Rol.ADMINISTRADOR, Rol.USUARIO)
    usuario = UsuarioActual(id=1, rol=Rol.USUARIO)

    assert dependencia(usuario=usuario) is usuario


def test_require_rol_rechaza_rol_no_autorizado():
    dependencia = require_rol(Rol.ADMINISTRADOR)
    usuario = UsuarioActual(id=1, rol=Rol.FISCALIZADOR)

    with pytest.raises(HTTPException) as exc_info:
        dependencia(usuario=usuario)

    assert exc_info.value.status_code == 403
