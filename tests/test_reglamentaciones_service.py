from datetime import date
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.errors import Conflicto, ErrorValidacion, RecursoNoEncontrado
from app.schemas.reglamentacion import ReglaCreate, ReglaUpdate, ReglamentacionCreate
from app.services import reglamentaciones as service


def test_crear_reglamentacion_409_si_se_solapa(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_solapamiento", lambda *a, **k: True)

    with pytest.raises(Conflicto):
        service.crear_reglamentacion(
            session, ReglamentacionCreate(fecha_inicio=date(2026, 1, 1), fecha_fin=None)
        )


def test_crear_reglamentacion_422_si_fecha_fin_anterior_a_inicio():
    session = MagicMock()
    with pytest.raises(ErrorValidacion):
        service.crear_reglamentacion(
            session,
            ReglamentacionCreate(fecha_inicio=date(2026, 6, 1), fecha_fin=date(2026, 1, 1)),
        )


def test_crear_reglamentacion_ok(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "existe_solapamiento", lambda *a, **k: False)
    reglamentacion = MagicMock(id=4, fecha_inicio=date(2026, 1, 1), fecha_fin=None, reglas=[])
    monkeypatch.setattr(service.repo, "crear", lambda s, fi, ff: reglamentacion)

    resultado = service.crear_reglamentacion(
        session, ReglamentacionCreate(fecha_inicio=date(2026, 1, 1), fecha_fin=None)
    )

    assert resultado.id == 4
    session.commit.assert_called_once()


def test_obtener_vigente_404_si_no_hay_ninguna(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_vigente", lambda s, f: None)

    with pytest.raises(RecursoNoEncontrado):
        service.obtener_vigente(session, date(2026, 9, 13))


def test_crear_regla_en_veda_ignora_tallas_y_aplica_convencion(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_por_id", lambda s, i: MagicMock(id=i))
    monkeypatch.setattr(service, "obtener_especie_por_nombre", lambda s, n: MagicMock(id=2))

    capturado = {}

    def _crear_regla(s, reglamentacion_id, especie_id, en_veda, talla_min, talla_max):
        capturado.update(
            en_veda=en_veda, talla_min=talla_min, talla_max=talla_max
        )
        return MagicMock(id=1, en_veda=en_veda, talla_min=talla_min, talla_max=talla_max, especie=MagicMock(id=especie_id, nombre_especie="Dorado"))

    monkeypatch.setattr(service.repo, "crear_regla", _crear_regla)

    resultado = service.crear_regla(
        session, 4, ReglaCreate(especie="Dorado", veda=True, talla_minima=None, talla_maxima=None)
    )

    assert capturado == {"en_veda": True, "talla_min": 0.0, "talla_max": 9999.0}
    assert resultado.talla_minima == 0.0
    assert resultado.talla_maxima == 9999.0
    assert resultado.veda is True


def test_crear_regla_sin_veda_requiere_tallas(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_por_id", lambda s, i: MagicMock(id=i))
    monkeypatch.setattr(service, "obtener_especie_por_nombre", lambda s, n: MagicMock(id=1))

    with pytest.raises(ErrorValidacion):
        service.crear_regla(
            session, 4, ReglaCreate(especie="Sábalo", veda=False, talla_minima=None, talla_maxima=None)
        )


def test_crear_regla_404_si_reglamentacion_no_existe(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_por_id", lambda s, i: None)

    with pytest.raises(RecursoNoEncontrado):
        service.crear_regla(
            session, 999, ReglaCreate(especie="Sábalo", veda=True)
        )


def test_crear_regla_409_si_ya_existe_regla_para_esa_especie(monkeypatch):
    session = MagicMock()
    session.commit.side_effect = IntegrityError("INSERT", {}, Exception("duplicate"))
    monkeypatch.setattr(service.repo, "obtener_por_id", lambda s, i: MagicMock(id=i))
    monkeypatch.setattr(service, "obtener_especie_por_nombre", lambda s, n: MagicMock(id=1))
    monkeypatch.setattr(service.repo, "crear_regla", lambda *a, **k: MagicMock())

    with pytest.raises(Conflicto):
        service.crear_regla(session, 4, ReglaCreate(especie="Sábalo", veda=True))

    session.rollback.assert_called_once()


def test_actualizar_regla_404_si_no_existe(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_regla", lambda s, i: None)

    with pytest.raises(RecursoNoEncontrado):
        service.actualizar_regla(session, 999, ReglaUpdate(veda=True))


def test_eliminar_reglamentacion_404_si_no_existe(monkeypatch):
    session = MagicMock()
    monkeypatch.setattr(service.repo, "obtener_por_id", lambda s, i: None)

    with pytest.raises(RecursoNoEncontrado):
        service.eliminar_reglamentacion(session, 999)
