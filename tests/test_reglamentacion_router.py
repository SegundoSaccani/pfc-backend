from datetime import date

from app.core.auth import UsuarioActual, get_current_user
from app.core.errors import Conflicto, RecursoNoEncontrado
from app.core.roles import Rol
from app.main import app
from app.schemas.relevamiento import EspecieResumen
from app.schemas.reglamentacion import ReglaDetalle, ReglamentacionDetalle
from app.services import reglamentaciones as service


def _forzar_rol(rol: Rol):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(id=1, rol=rol)


def _limpiar_overrides():
    app.dependency_overrides.pop(get_current_user, None)


def test_post_reglamentaciones_prohibido_para_usuario(client):
    _forzar_rol(Rol.USUARIO)
    try:
        response = client.post(
            "/api/reglamentaciones", json={"fechaInicio": "2026-01-01", "fechaFin": None}
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_post_reglamentaciones_permitido_para_administrador(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)
    monkeypatch.setattr(
        service,
        "crear_reglamentacion",
        lambda db, payload: ReglamentacionDetalle(
            id=1, fecha_inicio=date(2026, 1, 1), fecha_fin=None, reglas=[]
        ),
    )
    try:
        response = client.post(
            "/api/reglamentaciones", json={"fechaInicio": "2026-01-01", "fechaFin": None}
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 201
    assert response.json()["id"] == 1


def test_get_reglamentacion_vigente_permitido_para_fiscalizador(client, monkeypatch):
    _forzar_rol(Rol.FISCALIZADOR)
    monkeypatch.setattr(
        service,
        "obtener_vigente",
        lambda db, fecha: ReglamentacionDetalle(
            id=4, fecha_inicio=date(2026, 1, 1), fecha_fin=None, reglas=[]
        ),
    )
    try:
        response = client.get("/api/reglamentacion")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json()["fechaInicio"] == "2026-01-01"


def test_get_reglamentaciones_historico_prohibido_para_fiscalizador(client):
    _forzar_rol(Rol.FISCALIZADOR)
    try:
        response = client.get("/api/reglamentaciones")
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_get_reglamentacion_vigente_404_si_no_hay_ninguna(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)

    def _raise(db, fecha):
        raise RecursoNoEncontrado("No hay reglamentación vigente para la fecha 2026-09-13.")

    monkeypatch.setattr(service, "obtener_vigente", _raise)
    try:
        response = client.get("/api/reglamentacion?fecha=2026-09-13")
    finally:
        _limpiar_overrides()

    assert response.status_code == 404
    assert response.json()["error"]["codigo"] == "RECURSO_NO_ENCONTRADO"


def test_put_reglamentacion_409_si_se_solapa(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)

    def _raise(db, reglamentacion_id, payload):
        raise Conflicto("La reglamentación se solapa en el tiempo con una reglamentación existente.")

    monkeypatch.setattr(service, "actualizar_reglamentacion", _raise)
    try:
        response = client.put(
            "/api/reglamentaciones/1", json={"fechaInicio": "2026-01-01", "fechaFin": None}
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 409
    assert response.json()["error"]["codigo"] == "CONFLICTO"


def test_delete_reglamentacion_prohibido_para_usuario(client):
    _forzar_rol(Rol.USUARIO)
    try:
        response = client.delete("/api/reglamentaciones/1")
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_delete_reglamentacion_ok_para_administrador(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)
    monkeypatch.setattr(service, "eliminar_reglamentacion", lambda db, id_: None)
    try:
        response = client.delete("/api/reglamentaciones/1")
    finally:
        _limpiar_overrides()

    assert response.status_code == 204


def test_post_regla_409_si_ya_existe_para_esa_especie(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)

    def _raise(db, reglamentacion_id, payload):
        raise Conflicto("Ya existe una regla para esta especie en esta reglamentación.")

    monkeypatch.setattr(service, "crear_regla", _raise)
    try:
        response = client.post(
            "/api/reglamentaciones/1/reglas", json={"especieId": 1, "veda": True}
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 409


def test_post_regla_prohibido_para_fiscalizador(client):
    _forzar_rol(Rol.FISCALIZADOR)
    try:
        response = client.post(
            "/api/reglamentaciones/1/reglas", json={"especieId": 1, "veda": True}
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_put_regla_ok(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)
    monkeypatch.setattr(
        service,
        "actualizar_regla",
        lambda db, regla_id, payload: ReglaDetalle(
            id=regla_id, especie=EspecieResumen(id=1, nombre="Sábalo"), talla_minima=0.0, talla_maxima=9999.0, veda=True
        ),
    )
    try:
        response = client.put("/api/reglas/15", json={"veda": True})
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json()["veda"] is True


def test_delete_regla_404_si_no_existe(client, monkeypatch):
    _forzar_rol(Rol.ADMINISTRADOR)

    def _raise(db, regla_id):
        raise RecursoNoEncontrado(f"No existe la regla {regla_id}.")

    monkeypatch.setattr(service, "eliminar_regla", _raise)
    try:
        response = client.delete("/api/reglas/999")
    finally:
        _limpiar_overrides()

    assert response.status_code == 404
