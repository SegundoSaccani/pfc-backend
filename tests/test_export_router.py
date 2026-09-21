from app.core.auth import UsuarioActual, get_current_user
from app.core.roles import Rol
from app.main import app
from app.services import export as service


def _forzar_rol(rol: Rol):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(id=1, rol=rol)


def _limpiar_overrides():
    app.dependency_overrides.pop(get_current_user, None)


def _csv_falso():
    def _gen():
        yield b"col1,col2\r\n"
        yield b"1,2\r\n"

    return _gen(), "archivo.csv"


def test_export_relevamientos_matchea_antes_que_detalle_por_id(client, monkeypatch):
    # Regresion: "/api/relevamientos/export" no debe caer en la ruta "/{relevamiento_id}".
    _forzar_rol(Rol.USUARIO)
    monkeypatch.setattr(service, "exportar_relevamientos", lambda db, filtros: _csv_falso())
    try:
        response = client.get("/api/relevamientos/export")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")


def test_export_relevamientos_prohibido_para_fiscalizador(client):
    _forzar_rol(Rol.FISCALIZADOR)
    try:
        response = client.get("/api/relevamientos/export")
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_export_relevamientos_incluye_content_disposition(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)
    monkeypatch.setattr(service, "exportar_relevamientos", lambda db, filtros: _csv_falso())
    try:
        response = client.get("/api/relevamientos/export")
    finally:
        _limpiar_overrides()

    assert 'attachment; filename="archivo.csv"' == response.headers["content-disposition"]


def test_export_indicador_desconocido_devuelve_422(client):
    _forzar_rol(Rol.USUARIO)
    try:
        response = client.get("/api/indicadores/no-existe/export")
    finally:
        _limpiar_overrides()

    assert response.status_code == 422


def test_export_indicador_valido(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)
    monkeypatch.setattr(
        service, "exportar_indicador", lambda db, indicador, filtros, agrupacion: _csv_falso()
    )
    try:
        response = client.get("/api/indicadores/capturas-por-especie/export")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
