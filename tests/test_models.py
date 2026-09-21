from app.db.base import Base
from app.models import (
    EspeciePescado,
    Fiscalizador,
    PescadoIndividuo,
    Pescador,
    PuntoDesembarco,
    Regla,
    Reglamentacion,
    Relevamiento,
)


def _columns(model) -> set[str]:
    return {c.name for c in model.__table__.columns}


def test_all_expected_tables_are_registered():
    nombres_tablas = {t.name for t in Base.metadata.sorted_tables}
    assert nombres_tablas == {
        "Especie_Pescado",
        "Pescador",
        "Pescado_individuo",
        "Relevamiento",
        "Reglamentacion",
        "Regla",
        "Fiscalizador",
        "Punto_desembarco",
    }


def test_punto_desembarco_has_forma_migrada():
    assert _columns(PuntoDesembarco) == {"id", "nombre", "numero_orden"}
    assert PuntoDesembarco.__table__.c.nombre.unique


def test_relevamiento_tiene_unique_constraint_de_duplicados():
    nombres_constraints = {
        c.name for c in Relevamiento.__table__.constraints if c.name is not None
    }
    assert "relevamiento_fecha_hora_id_pescador_id_fiscalizador_unique" in nombres_constraints


def test_regla_tiene_unique_constraint_por_especie():
    nombres_constraints = {c.name for c in Regla.__table__.constraints if c.name is not None}
    assert "regla_id_reglamentacion_id_especie_unique" in nombres_constraints


def test_reglamentacion_mapea_columnas_camelcase_existentes():
    assert Reglamentacion.__table__.c["fechaInicio"] is not None
    assert Reglamentacion.__table__.c["fechaFin"] is not None


def test_pescado_individuo_referencia_relevamiento_y_especie():
    fks = {fk.column.table.name for fk in PescadoIndividuo.__table__.foreign_keys}
    assert fks == {"Relevamiento", "Especie_Pescado"}


def test_especie_pescado_nombre_unico():
    assert EspeciePescado.__table__.c.nombre_especie.unique


def test_fiscalizador_y_pescador_no_se_mezclan():
    assert _columns(Fiscalizador) == {"id", "nombre_user"}
    assert _columns(Pescador) == {"id", "nro_pescador"}
