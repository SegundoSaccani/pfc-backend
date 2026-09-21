from enum import Enum

from app.schemas.base import CamelModel


class Agrupacion(str, Enum):
    DIA = "dia"
    MES = "mes"
    ANIO = "anio"


class IndicadorExportable(str, Enum):
    CAPTURAS_POR_ESPECIE = "capturas-por-especie"
    CAPTURAS_POR_PUNTO = "capturas-por-punto"
    EVOLUCION_TEMPORAL = "evolucion-temporal"


class CapturaPorEspecieItem(CamelModel):
    especie_id: int
    nombre_especie: str
    cantidad: int


class CapturasPorEspecieResponse(CamelModel):
    datos: list[CapturaPorEspecieItem]
    # Adición sobre el ejemplo de api_spec.txt (PLAN.md sección 4): cantidad de relevamientos
    # excluidos del cálculo por fecha inválida/incompleta. Con el schema actual (fecha_hora
    # NOT NULL, validada en la carga) siempre da 0 — ver limitación en PLAN.md.
    excluidos: int


class CapturaPorEspecieDesglose(CamelModel):
    especie_id: int
    nombre_especie: str
    cantidad: int


class CapturaPorPuntoItem(CamelModel):
    punto_desembarco_id: int
    nombre: str
    cantidad: int
    # Presente solo cuando no se filtró por especieId (PLAN.md sección 2.4 / 4).
    por_especie: list[CapturaPorEspecieDesglose] | None = None


class CapturasPorPuntoResponse(CamelModel):
    datos: list[CapturaPorPuntoItem]
    excluidos: int


class EvolucionTemporalItem(CamelModel):
    periodo: str
    cantidad: int


class EvolucionTemporalResponse(CamelModel):
    agrupacion: Agrupacion
    datos: list[EvolucionTemporalItem]
    excluidos: int
