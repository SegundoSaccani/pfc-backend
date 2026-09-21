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


def _validar_referencias(session: Session, payload: RelevamientoCreate) -> int | None:
    detalles = []

    if not repo.existe_pescador(session, payload.pescador_id):
        detalles.append({"campo": "pescadorId", "mensaje": f"No existe el pescador {payload.pescador_id}."})

    if not repo.existe_fiscalizador(session, payload.fiscalizador_id):
        detalles.append(
            {"campo": "fiscalizadorId", "mensaje": f"No existe el fiscalizador {payload.fiscalizador_id}."}
        )

    for especie_id in {i.especie_id for i in payload.individuos}:
        if not repo.existe_especie(session, especie_id):
            detalles.append({"campo": "individuos.especieId", "mensaje": f"No existe la especie {especie_id}."})

    punto_desembarco_id = None
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
            punto_desembarco_id = punto.id

    if detalles:
        raise ErrorValidacion("Hay referencias inválidas en el relevamiento.", detalles)

    return punto_desembarco_id


def crear_relevamiento(session: Session, payload: RelevamientoCreate) -> RelevamientoCreateResponse:
    punto_desembarco_id = _validar_referencias(session, payload)

    valores = {
        "fecha_hora": payload.fecha_hora,
        "id_punto_desembarco": punto_desembarco_id,
        "ubicacion": ubicacion_a_geografia(payload.ubicacion),
        "id_pescador": payload.pescador_id,
        "id_fiscalizador": payload.fiscalizador_id,
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
                    "id_especie": individuo.especie_id,
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
