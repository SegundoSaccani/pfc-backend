from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.core.tz import hoy
from app.repositories import relevamientos as repo_relevamientos
from app.repositories.indicadores import FiltrosIndicador
from app.repositories.relevamientos import FiltrosRelevamiento
from app.schemas.indicadores import Agrupacion, IndicadorExportable
from app.services import indicadores as service_indicadores
from app.services.csv_export import generar_csv
from app.services.relevamiento_mappers import relevamiento_a_list_item

_ENCABEZADOS_RELEVAMIENTOS = [
    "id",
    "fechaHora",
    "puntoDesembarcoId",
    "puntoDesembarco",
    "latitud",
    "longitud",
    "fiscalizadorId",
    "fiscalizador",
    "cantidadIndividuos",
]


def exportar_relevamientos(
    session: Session, filtros: FiltrosRelevamiento
) -> tuple[Iterator[bytes], str]:
    relevamientos, conteos = repo_relevamientos.listar_para_exportar(session, filtros)

    # Se arma la lista completa ANTES de devolver el stream: StreamingResponse itera el body
    # después de que la sesión de DB de la request ya se cerró.
    filas = []
    for relevamiento in relevamientos:
        item = relevamiento_a_list_item(relevamiento, conteos.get(relevamiento.id, 0))
        filas.append(
            {
                "id": item.id,
                "fechaHora": item.fecha_hora.isoformat(),
                "puntoDesembarcoId": item.punto_desembarco.id if item.punto_desembarco else "",
                "puntoDesembarco": item.punto_desembarco.nombre if item.punto_desembarco else "",
                "latitud": item.ubicacion.latitud if item.ubicacion else "",
                "longitud": item.ubicacion.longitud if item.ubicacion else "",
                "fiscalizadorId": item.fiscalizador.id,
                "fiscalizador": item.fiscalizador.nombre_usuario,
                "cantidadIndividuos": item.cantidad_individuos,
            }
        )

    nombre_archivo = f"relevamientos_{hoy().isoformat()}.csv"
    return generar_csv(filas, _ENCABEZADOS_RELEVAMIENTOS), nombre_archivo


def exportar_indicador(
    session: Session,
    indicador: IndicadorExportable,
    filtros: FiltrosIndicador,
    agrupacion: Agrupacion,
) -> tuple[Iterator[bytes], str]:
    nombre_archivo = f"{indicador.value}_{hoy().isoformat()}.csv"

    if indicador is IndicadorExportable.CAPTURAS_POR_ESPECIE:
        resultado = service_indicadores.capturas_por_especie(session, filtros)
        encabezados = ["especieId", "nombreEspecie", "cantidad"]
        filas = [
            {"especieId": d.especie_id, "nombreEspecie": d.nombre_especie, "cantidad": d.cantidad}
            for d in resultado.datos
        ]
    elif indicador is IndicadorExportable.CAPTURAS_POR_PUNTO:
        resultado = service_indicadores.capturas_por_punto(session, filtros)
        encabezados = ["puntoDesembarcoId", "nombre", "cantidad"]
        filas = [
            {"puntoDesembarcoId": d.punto_desembarco_id, "nombre": d.nombre, "cantidad": d.cantidad}
            for d in resultado.datos
        ]
    else:
        resultado = service_indicadores.evolucion_temporal(session, agrupacion, filtros)
        encabezados = ["periodo", "cantidad"]
        filas = [{"periodo": d.periodo, "cantidad": d.cantidad} for d in resultado.datos]

    return generar_csv(filas, encabezados), nombre_archivo
