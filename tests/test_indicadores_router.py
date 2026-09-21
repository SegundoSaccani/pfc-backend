from app.core.auth import UsuarioActual, get_current_user
from app.core.roles import Rol
from app.main import app
from app.schemas.indicadores import Agrupacion, CapturasPorEspecieResponse, EvolucionTemporalResponse
from app.services import indicadores as service


def _forzar_rol(rol: Rol):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(id=1, rol=rol)


def _limpiar_overrides():
    app.dependency_overrides.pop(get_current_user, None)


def test_capturas_por_especie_prohibido_para_fiscalizador(client):
    _forzar_rol(Rol.FISCALIZADOR)
    try:
        response = client.get("/api/indicadores/capturas-por-especie")
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_capturas_por_especie_permitido_para_usuario(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)
    monkeypatch.setattr(
        service, "capturas_por_especie", lambda db, filtros: CapturasPorEspecieResponse(datos=[], excluidos=0)
    )
    try:
        response = client.get("/api/indicadores/capturas-por-especie")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json() == {"datos": [], "excluidos": 0}


def test_evolucion_temporal_requiere_agrupacion_valida(client):
    _forzar_rol(Rol.USUARIO)
    try:
        response = client.get("/api/indicadores/evolucion-temporal?agrupacion=semana")
    finally:
        _limpiar_overrides()

    assert response.status_code == 422
    assert response.json()["error"]["codigo"] == "ERROR_VALIDACION"


def test_evolucion_temporal_ok_con_agrupacion_valida(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)
    monkeypatch.setattr(
        service,
        "evolucion_temporal",
        lambda db, agrupacion, filtros: EvolucionTemporalResponse(
            agrupacion=agrupacion, datos=[], excluidos=0
        ),
    )
    try:
        response = client.get("/api/indicadores/evolucion-temporal?agrupacion=mes")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json()["agrupacion"] == "mes"
