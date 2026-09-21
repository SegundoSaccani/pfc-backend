from datetime import datetime

from app.schemas.base import CamelModel
from app.schemas.comunes import Ubicacion


class IndividuoCreate(CamelModel):
    especie_id: int
    talla: float
    confianza_especie: float | None = None


class RelevamientoCreate(CamelModel):
    fecha_hora: datetime
    punto_desembarco: str | None = None
    ubicacion: Ubicacion | None = None
    observaciones: str | None = None
    pescador_id: int
    # Temporal (PLAN.md sección 2.3 / CLAUDE.md): sin auth real, la app móvil manda el fiscalizador
    # en el body. Reemplazar por el usuario del token cuando exista auth.
    fiscalizador_id: int
    individuos: list[IndividuoCreate]


class RelevamientoCreateResponse(CamelModel):
    id: int
    estado: str


class EspecieResumen(CamelModel):
    id: int
    nombre: str


class PuntoDesembarcoResumen(CamelModel):
    id: int
    nombre: str


class FiscalizadorResumen(CamelModel):
    id: int
    nombre_usuario: str


class PescadorResumen(CamelModel):
    id: int
    nro_pescador: int


class RelevamientoListItem(CamelModel):
    id: int
    fecha_hora: datetime
    punto_desembarco: PuntoDesembarcoResumen | None
    ubicacion: Ubicacion | None
    fiscalizador: FiscalizadorResumen
    cantidad_individuos: int


class RelevamientoListResponse(CamelModel):
    items: list[RelevamientoListItem]
    page: int
    size: int
    total: int


class IndividuoDetalle(CamelModel):
    id: int
    especie: EspecieResumen
    talla: float
    confianza_especie: float | None


class RelevamientoDetalle(CamelModel):
    id: int
    fecha_hora: datetime
    punto_desembarco: PuntoDesembarcoResumen | None
    ubicacion: Ubicacion | None
    observaciones: str | None
    fiscalizador: FiscalizadorResumen
    pescador: PescadorResumen
    individuos: list[IndividuoDetalle]
