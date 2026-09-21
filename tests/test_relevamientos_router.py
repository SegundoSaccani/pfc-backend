from app.core.auth import get_current_user, UsuarioActual
from app.core.errors import ErrorValidacion, RecursoNoEncontrado
from app.core.roles import Rol
from app.main import app
from app.schemas.relevamiento import (
    EspecieResumen,
    FiscalizadorResumen,
    IndividuoDetalle,
    PescadorResumen,
    RelevamientoCreateResponse,
    RelevamientoDetalle,
    RelevamientoListResponse,
)
from app.services import relevamientos as service


def _forzar_rol(rol: Rol):
    app.dependency_overrides[get_current_user] = lambda: UsuarioActual(id=1, rol=rol)


def _limpiar_overrides():
    app.dependency_overrides.pop(get_current_user, None)


def test_post_relevamiento_devuelve_201_si_registrado(client, monkeypatch):
    _forzar_rol(Rol.FISCALIZADOR)
    monkeypatch.setattr(
        service,
        "crear_relevamiento",
        lambda db, payload: RelevamientoCreateResponse(id=125, estado="REGISTRADO"),
    )
    try:
        response = client.post(
            "/api/relevamientos",
            json={
                "fechaHora": "2026-09-13T18:30:00-03:00",
                "pescadorId": 145,
                "fiscalizadorId": 4,
                "individuos": [{"especieId": 1, "talla": 42.5}],
            },
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 201
    assert response.json() == {"id": 125, "estado": "REGISTRADO"}


def test_post_relevamiento_devuelve_200_si_duplicado(client, monkeypatch):
    _forzar_rol(Rol.FISCALIZADOR)
    monkeypatch.setattr(
        service,
        "crear_relevamiento",
        lambda db, payload: RelevamientoCreateResponse(id=125, estado="DUPLICADO"),
    )
    try:
        response = client.post(
            "/api/relevamientos",
            json={
                "fechaHora": "2026-09-13T18:30:00-03:00",
                "pescadorId": 145,
                "fiscalizadorId": 4,
                "individuos": [{"especieId": 1, "talla": 42.5}],
            },
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json()["estado"] == "DUPLICADO"


def test_post_relevamiento_prohibido_para_usuario(client):
    _forzar_rol(Rol.USUARIO)
    try:
        response = client.post(
            "/api/relevamientos",
            json={
                "fechaHora": "2026-09-13T18:30:00-03:00",
                "pescadorId": 145,
                "fiscalizadorId": 4,
                "individuos": [{"especieId": 1, "talla": 42.5}],
            },
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 403
    assert response.json()["error"]["codigo"] == "PROHIBIDO"


def test_get_relevamientos_prohibido_para_fiscalizador(client):
    _forzar_rol(Rol.FISCALIZADOR)
    try:
        response = client.get("/api/relevamientos")
    finally:
        _limpiar_overrides()

    assert response.status_code == 403


def test_get_relevamientos_sin_resultados(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)
    monkeypatch.setattr(
        service,
        "listar_relevamientos",
        lambda db, filtros, page, size: RelevamientoListResponse(items=[], page=0, size=20, total=0),
    )
    try:
        response = client.get("/api/relevamientos")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    assert response.json() == {"items": [], "page": 0, "size": 20, "total": 0}


def test_get_relevamiento_detalle_404(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)

    def _raise(db, relevamiento_id):
        raise RecursoNoEncontrado(f"No existe el relevamiento {relevamiento_id}.")

    monkeypatch.setattr(service, "obtener_relevamiento_detalle", _raise)
    try:
        response = client.get("/api/relevamientos/999")
    finally:
        _limpiar_overrides()

    assert response.status_code == 404
    assert response.json()["error"]["codigo"] == "RECURSO_NO_ENCONTRADO"


def test_get_relevamiento_detalle_happy_path(client, monkeypatch):
    _forzar_rol(Rol.USUARIO)
    detalle = RelevamientoDetalle(
        id=125,
        fecha_hora="2026-09-13T18:30:00-03:00",
        punto_desembarco=None,
        ubicacion=None,
        observaciones="Sin observaciones",
        fiscalizador=FiscalizadorResumen(id=4, nombre_usuario="fiscalizador1"),
        pescador=PescadorResumen(id=145, nro_pescador=145),
        individuos=[
            IndividuoDetalle(
                id=501, especie=EspecieResumen(id=1, nombre="Sábalo"), talla=42.5, confianza_especie=None
            )
        ],
    )
    monkeypatch.setattr(service, "obtener_relevamiento_detalle", lambda db, id_: detalle)
    try:
        response = client.get("/api/relevamientos/125")
    finally:
        _limpiar_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == 125
    assert body["pescador"] == {"id": 145, "nroPescador": 145}
    assert body["individuos"][0]["especie"]["nombre"] == "Sábalo"


def test_post_relevamiento_422_si_referencias_invalidas(client, monkeypatch):
    _forzar_rol(Rol.FISCALIZADOR)

    def _raise(db, payload):
        raise ErrorValidacion(
            "Hay referencias inválidas en el relevamiento.",
            [{"campo": "pescadorId", "mensaje": "No existe el pescador 999."}],
        )

    monkeypatch.setattr(service, "crear_relevamiento", _raise)
    try:
        response = client.post(
            "/api/relevamientos",
            json={
                "fechaHora": "2026-09-13T18:30:00-03:00",
                "pescadorId": 999,
                "fiscalizadorId": 4,
                "individuos": [{"especieId": 1, "talla": 42.5}],
            },
        )
    finally:
        _limpiar_overrides()

    assert response.status_code == 422
    assert response.json()["error"]["codigo"] == "ERROR_VALIDACION"
