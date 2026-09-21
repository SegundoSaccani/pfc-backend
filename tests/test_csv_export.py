from app.services.csv_export import generar_csv


def test_generar_csv_incluye_bom_encabezado_y_filas():
    filas = [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
    contenido = b"".join(generar_csv(filas, ["a", "b"]))

    assert contenido.startswith("﻿".encode("utf-8"))
    texto = contenido.decode("utf-8-sig")
    lineas = texto.splitlines()
    assert lineas[0] == "a,b"
    assert lineas[1] == "1,x"
    assert lineas[2] == "2,y"


def test_generar_csv_sin_filas_solo_tiene_encabezado():
    contenido = b"".join(generar_csv([], ["a", "b"]))
    texto = contenido.decode("utf-8-sig")
    assert texto.strip() == "a,b"
