from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.errors import ErrorValidacion, RecursoNoEncontrado
from app.repositories import relevamientos as repo
from app.schemas.relevamiento import (
    RelevamientoCreate,
    RelevamientoCreateResponse,
    RelevamientoDetalle,
    RelevamientoListResponse,
)
from app.services.geo import ubicacion_a_geografia
from app.services.relevamiento_mappers import relevamiento_a_detalle, relevamiento_a_list_item


@dataclass
class _ReferenciasResueltas:
    id_pescador: int
    id_fiscalizador: int
    id_punto_desembarco: int | None
    id_especie_por_nombre: dict[str, int]


def _validar_referencias(session: Session, payload: RelevamientoCreate) -> _ReferenciasResueltas:
    # Todas las referencias externas se resuelven por clave de negocio (unique), nunca por el id
    # interno de la tabla: los id son correlativos generados por el motor, sin significado fuera de
    # la base (CLAUDE.md).
    detalles = []

    pescador = repo.obtener_pescador_por_nro(session, payload.nro_pescador)
    if pescador is None:
        detalles.append(
            {"campo": "nroPescador", "mensaje": f"No existe el pescador con nro_pescador {payload.nro_pescador}."}
        )

    fiscalizador = repo.obtener_fiscalizador_por_nombre_user(session, payload.fiscalizador)
    if fiscalizador is None:
        detalles.append(
            {"campo": "fiscalizador", "mensaje": f"No existe el fiscalizador '{payload.fiscalizador}'."}
        )

    id_especie_por_nombre: dict[str, int] = {}
    for nombre_especie in {i.especie for i in payload.individuos}:
        especie = repo.obtener_especie_por_nombre(session, nombre_especie)
        if especie is None:
            detalles.append({"campo": "individuos.especie", "mensaje": f"No existe la especie '{nombre_especie}'."})
        else:
            id_especie_por_nombre[nombre_especie] = especie.id

    id_punto_desembarco = None
    if payload.punto_desembarco is not None:
        punto = repo.obtener_punto_desembarco_por_nombre(session, payload.punto_desembarco)
        if punto is None:
            detalles.append(
                {
                    "campo": "puntoDesembarco",
                    "mensaje": f"No existe el punto de desembarco '{payload.punto_desembarco}'.",
                }
            )
        else:
            id_punto_desembarco = punto.id

    if detalles:
        raise ErrorValidacion("Hay referencias inválidas en el relevamiento.", detalles)

    return _ReferenciasResueltas(
        id_pescador=pescador.id,
        id_fiscalizador=fiscalizador.id,
        id_punto_desembarco=id_punto_desembarco,
        id_especie_por_nombre=id_especie_por_nombre,
    )


def crear_relevamiento(session: Session, payload: RelevamientoCreate) -> RelevamientoCreateResponse:
    referencias = _validar_referencias(session, payload)

    valores = {
        "fecha_hora": payload.fecha_hora,
        "id_punto_desembarco": referencias.id_punto_desembarco,
        "ubicacion": ubicacion_a_geografia(payload.ubicacion),
        "id_pescador": referencias.id_pescador,
        "id_fiscalizador": referencias.id_fiscalizador,
        "observaciones": payload.observaciones,
    }

    relevamiento_id, es_nuevo = repo.insertar_relevamiento_o_duplicado(session, valores)

    if es_nuevo:
        repo.insertar_individuos(
            session,
            relevamiento_id,
            [
                {
                    "talla": individuo.talla,
                    "confianza_especie": individuo.confianza_especie,
                    "id_especie": referencias.id_especie_por_nombre[individuo.especie],
                }
                for individuo in payload.individuos
            ],
        )

    session.commit()

    return RelevamientoCreateResponse(
        id=relevamiento_id, estado="REGISTRADO" if es_nuevo else "DUPLICADO"
    )


def listar_relevamientos(
    session: Session, filtros: repo.FiltrosRelevamiento, page: int, size: int
) -> RelevamientoListResponse:
    relevamientos, conteos, total = repo.listar(session, filtros, page, size)
    items = [
        relevamiento_a_list_item(r, conteos.get(r.id, 0)) for r in relevamientos
    ]
    return RelevamientoListResponse(items=items, page=page, size=size, total=total)


def obtener_relevamiento_detalle(session: Session, relevamiento_id: int) -> RelevamientoDetalle:
    relevamiento = repo.obtener_detalle(session, relevamiento_id)
    if relevamiento is None:
        raise RecursoNoEncontrado(f"No existe el relevamiento {relevamiento_id}.")
    return relevamiento_a_detalle(relevamiento)
