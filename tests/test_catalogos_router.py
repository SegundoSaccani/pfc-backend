from unittest.mock import MagicMock

from app.core.auth import UsuarioActual, get_current_user
from app.core.roles import Rol
from app.db.session import get_db
from app.main import app


def _forzar_rol(rol: Rol):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(id=1, rol=rol)


def _forzar_db_con_filas(filas):
    fake_scalars = MagicMock()
    fake_scalars.all.return_value = filas
    fake_session = MagicMock()
    fake_session.scalars.return_value = fake_scalars

    def _override():
        yield fake_session

    app.dependency_overrides[get_db] = _override


def _limpiar_overrides():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


def test_listar_especies(client):
    _forzar_rol(Rol.USUARIO)
    especie = MagicMock(id=1, nombre_especie="Sábalo")
    _forzar_db_con_filas([especie])
    try:
        response = client.get("/api/especies")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json() == [{"id": 1, "nombre": "Sábalo"}]


def test_listar_puntos_desembarco_sin_ubicacion(client):
    _forzar_rol(Rol.FISCALIZADOR)
    punto = MagicMock(id=1, nombre="Puerto de Santa Fe")
    _forzar_db_con_filas([punto])
    try:
        response = client.get("/api/puntos-desembarco")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body == [{"id": 1, "nombre": "Puerto de Santa Fe"}]
    assert "ubicacion" not in body[0]
