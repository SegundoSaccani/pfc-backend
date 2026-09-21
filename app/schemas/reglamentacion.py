from datetime import date

from app.schemas.base import CamelModel
from app.schemas.relevamiento import EspecieResumen


class ReglamentacionCreate(CamelModel):
    fecha_inicio: date
    fecha_fin: date | None = None


class ReglamentacionResumen(CamelModel):
    id: int
    fecha_inicio: date
    fecha_fin: date | None


class ReglaCreate(CamelModel):
    especie_id: int
    veda: bool
    # Obligatorias solo si veda=false; si veda=true se ignoran y se guarda la convención 0/9999
    # (PLAN.md sección 2 / CLAUDE.md: en_veda NOT NULL en la base, tallas siempre numéricas).
    talla_minima: float | None = None
    talla_maxima: float | None = None


class ReglaUpdate(CamelModel):
    especie_id: int | None = None
    veda: bool
    talla_minima: float | None = None
    talla_maxima: float | None = None


class ReglaDetalle(CamelModel):
    id: int
    especie: EspecieResumen
    talla_minima: float
    talla_maxima: float
    veda: bool


class ReglamentacionDetalle(CamelModel):
    id: int
    fecha_inicio: date
    fecha_fin: date | None
    reglas: list[ReglaDetalle]
