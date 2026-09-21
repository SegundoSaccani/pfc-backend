"""Verifica que las queries de indicadores compilen contra el dialecto de Postgres.

No hay una instancia real de Postgres/Neon disponible en este entorno (PLAN.md), así que esto no
reemplaza probar la semántica contra datos reales -- pero sí detecta errores estructurales (nombres
de columna/tabla, joins mal formados, uso incorrecto de generate_series/date_trunc) sin necesitar
una conexión.
"""

from datetime import date, datetime

from sqlalchemy.dialects import postgresql

from app.repositories.indicadores import (
    FiltrosIndicador,
    _construir_capturas_por_especie,
    _construir_capturas_por_punto,
    _construir_capturas_por_punto_desglose_especie,
    _construir_evolucion_temporal,
)


def _compila(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect()))


def test_capturas_por_especie_compila_con_todos_los_filtros():
    filtros = FiltrosIndicador(
        fecha_desde=date(2026, 1, 1), fecha_hasta=date(2026, 9, 30), especie_id=1, punto_desembarco_id=2
    )
    sql = _compila(_construir_capturas_por_especie(filtros))
    assert "Especie_Pescado" in sql
    assert "GROUP BY" in sql


def test_capturas_por_punto_usa_left_join_para_zero_fill():
    sql = _compila(_construir_capturas_por_punto(FiltrosIndicador()))
    assert "LEFT OUTER JOIN" in sql
    assert '"Punto_desembarco"' in sql
    assert "numero_orden" in sql


def test_capturas_por_punto_con_filtro_de_punto_restringe_en_where_no_en_join():
    filtros = FiltrosIndicador(punto_desembarco_id=2)
    sql = _compila(_construir_capturas_por_punto(filtros))
    assert "WHERE" in sql
    where_clause = sql.split("WHERE", 1)[1]
    assert '"Punto_desembarco".id' in where_clause


def test_capturas_por_punto_desglose_especie_usa_inner_joins():
    sql = _compila(_construir_capturas_por_punto_desglose_especie(FiltrosIndicador()))
    assert "LEFT OUTER JOIN" not in sql
    assert "JOIN" in sql


def test_evolucion_temporal_usa_generate_series_y_timezone():
    sql = _compila(
        _construir_evolucion_temporal(
            FiltrosIndicador(), "month", datetime(2026, 1, 1), datetime(2026, 9, 1)
        )
    )
    assert "generate_series" in sql
    assert "timezone" in sql
    assert "date_trunc" in sql
    assert "coalesce" in sql
