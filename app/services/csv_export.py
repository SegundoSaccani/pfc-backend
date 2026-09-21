import csv
import io
from collections.abc import Iterable, Iterator


def generar_csv(filas: Iterable[dict], encabezados: list[str]) -> Iterator[bytes]:
    """Genera un CSV UTF-8 con BOM (para que Excel lo abra bien) como stream de bytes.

    `filas` debe ser datos ya materializados (dicts), no un generador que siga leyendo de la
    sesión de SQLAlchemy: StreamingResponse itera el body después de que las dependencias de la
    request (incluida la sesión de DB) ya se cerraron.
    """
    yield "﻿".encode("utf-8")

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=encabezados)

    writer.writeheader()
    yield buffer.getvalue().encode("utf-8")
    buffer.seek(0)
    buffer.truncate(0)

    for fila in filas:
        writer.writerow(fila)
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)
