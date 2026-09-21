from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.repositories.indicadores import FiltrosIndicador
from app.repositories.relevamientos import FiltrosRelevamiento
from app.schemas.indicadores import Agrupacion, CapturaPorEspecieItem, CapturasPorEspecieResponse, IndicadorExportable
from app.services import export as service


def test_exportar_relevamientos_arma_filas_planas(monkeypatch):
    session = MagicMock()
    relevamiento = MagicMock(
        id=125,
        fecha_hora=datetime(2026, 9, 13, 18, 30, tzinfo=timezone.utc),
        observaciones=None,
    )
    relevamiento.punto_desembarco = MagicMock(id=3, nombre="Puerto de Santa Fe")
    relevamiento.fiscalizador = MagicMock(id=4, nombre_user="fiscalizador1")
    relevamiento.ubicacion = None
    monkeypatch.setattr(
        service.repo_relevamientos, "listar_para_exportar", lambda s, f: ([relevamiento], {125: 2})
    )

    filas_iter, nombre_archivo = service.exportar_relevamientos(session, FiltrosRelevamiento())
    contenido = b"".join(filas_iter).decode("utf-8-sig")

    assert nombre_archivo.startswith("relevamientos_")
    assert "125" in contenido
    assert "Puerto de Santa Fe" in contenido
    assert "fiscalizador1" in contenido
    assert "2" in contenido  # cantidadIndividuos


def test_exportar_indicador_capturas_por_especie(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(
        service.service_indicadores,
        "capturas_por_especie",
        lambda s, f: CapturasPorEspecieResponse(
            datos=[CapturaPorEspecieItem(especie_id=1, nombre_especie="Sábalo", cantidad=146)],
            excluidos=0,
        ),
    )

    filas_iter, nombre_archivo = service.exportar_indicador(
        session, IndicadorExportable.CAPTURAS_POR_ESPECIE, FiltrosIndicador(), Agrupacion.MES
    )
    contenido = b"".join(filas_iter).decode("utf-8-sig")

    assert nombre_archivo.startswith("capturas-por-especie_")
    assert "Sábalo" in contenido
    assert "146" in contenido
