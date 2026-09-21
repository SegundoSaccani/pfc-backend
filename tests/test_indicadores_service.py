from datetime import datetime
from unittest.mock import MagicMock

from app.repositories.indicadores import FiltrosIndicador
from app.schemas.indicadores import Agrupacion
from app.services import indicadores as service


def test_capturas_por_especie_mapea_filas(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "capturas_por_especie", lambda s, f: [(1, "Sábalo", 146)])

    resultado = service.capturas_por_especie(session, FiltrosIndicador())

    assert resultado.excluidos == 0
    assert resultado.datos == [service.CapturaPorEspecieItem(especie_id=1, nombre_especie="Sábalo", cantidad=146)]


def test_capturas_por_punto_incluye_puntos_en_cero(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(
        service.repo,
        "capturas_por_punto",
        lambda s, f: [(1, "Puerto de Santa Fe", 210), (2, "Desvío Arijón", 0)],
    )
    monkeypatch.setattr(service.repo, "capturas_por_punto_desglose_especie", lambda s, f: [])

    resultado = service.capturas_por_punto(session, FiltrosIndicador())

    cantidades = {item.punto_desembarco_id: item.cantidad for item in resultado.datos}
    assert cantidades == {1: 210, 2: 0}


def test_capturas_por_punto_arma_desglose_por_especie_si_no_hay_filtro_de_especie(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "capturas_por_punto", lambda s, f: [(1, "Puerto de Santa Fe", 5)])
    monkeypatch.setattr(
        service.repo,
        "capturas_por_punto_desglose_especie",
        lambda s, f: [(1, 1, "Sábalo", 3), (1, 2, "Surubí", 2)],
    )

    resultado = service.capturas_por_punto(session, FiltrosIndicador())

    item = resultado.datos[0]
    assert item.por_especie is not None
    assert {d.nombre_especie for d in item.por_especie} == {"Sábalo", "Surubí"}


def test_capturas_por_punto_no_arma_desglose_si_hay_filtro_de_especie(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "capturas_por_punto", lambda s, f: [(1, "Puerto de Santa Fe", 3)])
    llamado = MagicMock()
    monkeypatch.setattr(service.repo, "capturas_por_punto_desglose_especie", llamado)

    resultado = service.capturas_por_punto(session, FiltrosIndicador(especie_id=1))

    llamado.assert_not_called()
    assert resultado.datos[0].por_especie is None


def test_evolucion_temporal_serializa_periodos_segun_agrupacion(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(
        service.repo,
        "evolucion_temporal",
        lambda s, agrupacion, f: [
            (datetime(2026, 7, 1), 340),
            (datetime(2026, 8, 1), 415),
            (datetime(2026, 9, 1), 0),
        ],
    )

    resultado = service.evolucion_temporal(session, Agrupacion.MES, FiltrosIndicador())

    assert resultado.agrupacion == Agrupacion.MES
    assert [d.periodo for d in resultado.datos] == ["2026-07", "2026-08", "2026-09"]
    assert [d.cantidad for d in resultado.datos] == [340, 415, 0]


def test_evolucion_temporal_sin_datos_devuelve_lista_vacia(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "evolucion_temporal", lambda s, agrupacion, f: [])

    resultado = service.evolucion_temporal(session, Agrupacion.DIA, FiltrosIndicador())

    assert resultado.datos == []
