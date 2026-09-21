from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from app.core.errors import ErrorValidacion, RecursoNoEncontrado
from app.repositories.relevamientos import FiltrosRelevamiento
from app.schemas.comunes import Ubicacion
from app.schemas.relevamiento import IndividuoCreate, RelevamientoCreate
from app.services import relevamientos as service


def _payload(**overrides) -> RelevamientoCreate:
    base = dict(
        fecha_hora=datetime(2026, 9, 13, 18, 30, tzinfo=timezone.utc),
        punto_desembarco="Puerto de Santa Fe",
        ubicacion=Ubicacion(latitud=-31.633, longitud=-60.699),
        observaciones="Sin observaciones",
        pescador_id=145,
        fiscalizador_id=4,
        individuos=[IndividuoCreate(especie_id=1, talla=42.5, confianza_especie=None)],
    )
    base.update(overrides)
    return RelevamientoCreate(**base)


def test_crear_relevamiento_falla_422_si_referencias_no_existen(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_pescador", lambda s, i: False)
    monkeypatch.setattr(service.repo, "existe_fiscalizador", lambda s, i: False)
    monkeypatch.setattr(service.repo, "existe_especie", lambda s, i: False)
    monkeypatch.setattr(service.repo, "obtener_punto_desembarco_por_nombre", lambda s, n: None)

    with pytest.raises(ErrorValidacion) as exc_info:
        service.crear_relevamiento(session, _payload())

    campos = {d["campo"] for d in exc_info.value.detalles}
    assert campos == {"pescadorId", "fiscalizadorId", "individuos.especieId", "puntoDesembarco"}


def test_crear_relevamiento_nuevo_devuelve_registrado(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_pescador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_fiscalizador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_especie", lambda s, i: True)
    punto = MagicMock(id=3)
    monkeypatch.setattr(service.repo, "obtener_punto_desembarco_por_nombre", lambda s, n: punto)
    monkeypatch.setattr(service.repo, "insertar_relevamiento_o_duplicado", lambda s, v: (125, True))
    insertar_individuos = MagicMock()
    monkeypatch.setattr(service.repo, "insertar_individuos", insertar_individuos)

    resultado = service.crear_relevamiento(session, _payload())

    assert resultado.id == 125
    assert resultado.estado == "REGISTRADO"
    insertar_individuos.assert_called_once()
    session.commit.assert_called_once()


def test_crear_relevamiento_duplicado_no_inserta_individuos(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_pescador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_fiscalizador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_especie", lambda s, i: True)
    monkeypatch.setattr(service.repo, "obtener_punto_desembarco_por_nombre", lambda s, n: MagicMock(id=3))
    monkeypatch.setattr(service.repo, "insertar_relevamiento_o_duplicado", lambda s, v: (125, False))
    insertar_individuos = MagicMock()
    monkeypatch.setattr(service.repo, "insertar_individuos", insertar_individuos)

    resultado = service.crear_relevamiento(session, _payload())

    assert resultado.id == 125
    assert resultado.estado == "DUPLICADO"
    insertar_individuos.assert_not_called()


def test_crear_relevamiento_sin_punto_desembarco_no_valida_nombre(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_pescador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_fiscalizador", lambda s, i: True)
    monkeypatch.setattr(service.repo, "existe_especie", lambda s, i: True)
    llamado = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_punto_desembarco_por_nombre", llamado)
    monkeypatch.setattr(service.repo, "insertar_relevamiento_o_duplicado", lambda s, v: (1, True))
    monkeypatch.setattr(service.repo, "insertar_individuos", MagicMock())

    service.crear_relevamiento(session, _payload(punto_desembarco=None, ubicacion=None))

    llamado.assert_not_called()


def test_obtener_relevamiento_detalle_404_si_no_existe(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_detalle", lambda s, i: None)

    with pytest.raises(RecursoNoEncontrado):
        service.obtener_relevamiento_detalle(session, 999)


def test_listar_relevamientos_sin_resultados_devuelve_lista_vacia(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "listar", lambda s, f, p, sz: ([], {}, 0))

    resultado = service.listar_relevamientos(session, FiltrosRelevamiento(), page=0, size=20)

    assert resultado.items == []
    assert resultado.total == 0
    assert resultado.page == 0
    assert resultado.size == 20
