"""Datos de seed para Especie_Pescado y Punto_desembarco.

PLAN.md sección 6: todavía no existen las listas reales. Se deja la estructura lista para
completar con los datos que confirme el usuario; no se inventan valores de ejemplo.
"""

from sqlalchemy.orm import Session

from app.models import EspeciePescado, PuntoDesembarco

ESPECIES: list[str] = []

# Cada tupla es (nombre, numero_orden).
PUNTOS_DESEMBARCO: list[tuple[str, int]] = []


def seed(session: Session) -> None:
    for nombre_especie in ESPECIES:
        existente = session.query(EspeciePescado).filter_by(nombre_especie=nombre_especie).first()
        if existente is None:
            session.add(EspeciePescado(nombre_especie=nombre_especie))

    for nombre, numero_orden in PUNTOS_DESEMBARCO:
        existente = session.query(PuntoDesembarco).filter_by(nombre=nombre).first()
        if existente is None:
            session.add(PuntoDesembarco(nombre=nombre, numero_orden=numero_orden))

    session.commit()
