from app.models import EspeciePescado, Fiscalizador, Pescador, PescadoIndividuo, PuntoDesembarco, Relevamiento
from app.schemas.relevamiento import (
    EspecieResumen,
    FiscalizadorResumen,
    IndividuoDetalle,
    PescadorResumen,
    PuntoDesembarcoResumen,
    RelevamientoDetalle,
    RelevamientoListItem,
)
from app.services.geo import geografia_a_ubicacion


def especie_a_resumen(especie: EspeciePescado) -> EspecieResumen:
    return EspecieResumen(id=especie.id, nombre=especie.nombre_especie)


def punto_a_resumen(punto: PuntoDesembarco | None) -> PuntoDesembarcoResumen | None:
    if punto is None:
        return None
    return PuntoDesembarcoResumen(id=punto.id, nombre=punto.nombre)


def fiscalizador_a_resumen(fiscalizador: Fiscalizador) -> FiscalizadorResumen:
    return FiscalizadorResumen(id=fiscalizador.id, nombre_usuario=fiscalizador.nombre_user)


def pescador_a_resumen(pescador: Pescador) -> PescadorResumen:
    return PescadorResumen(id=pescador.id, nro_pescador=pescador.nro_pescador)


def individuo_a_detalle(individuo: PescadoIndividuo) -> IndividuoDetalle:
    return IndividuoDetalle(
        id=individuo.id,
        especie=especie_a_resumen(individuo.especie),
        talla=individuo.talla,
        confianza_especie=individuo.confianza_especie,
    )


def relevamiento_a_list_item(relevamiento: Relevamiento, cantidad_individuos: int) -> RelevamientoListItem:
    return RelevamientoListItem(
        id=relevamiento.id,
        fecha_hora=relevamiento.fecha_hora,
        punto_desembarco=punto_a_resumen(relevamiento.punto_desembarco),
        ubicacion=geografia_a_ubicacion(relevamiento.ubicacion),
        fiscalizador=fiscalizador_a_resumen(relevamiento.fiscalizador),
        cantidad_individuos=cantidad_individuos,
    )


def relevamiento_a_detalle(relevamiento: Relevamiento) -> RelevamientoDetalle:
    return RelevamientoDetalle(
        id=relevamiento.id,
        fecha_hora=relevamiento.fecha_hora,
        punto_desembarco=punto_a_resumen(relevamiento.punto_desembarco),
        ubicacion=geografia_a_ubicacion(relevamiento.ubicacion),
        observaciones=relevamiento.observaciones,
        fiscalizador=fiscalizador_a_resumen(relevamiento.fiscalizador),
        pescador=pescador_a_resumen(relevamiento.pescador),
        individuos=[individuo_a_detalle(i) for i in relevamiento.individuos],
    )
