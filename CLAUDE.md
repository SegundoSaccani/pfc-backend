# CLAUDE.md

Backend API para el sistema de relevamiento de pesca artesanal (proyecto de carrera). Única puerta
de entrada a los datos para la app móvil (fiscalizadores) y la web (investigadores/Ministerio).
Contexto completo del proyecto, decisiones y limitaciones conocidas: ver [PLAN.md](PLAN.md),
[schema.sql](schema.sql) y [api_spec.txt](api_spec.txt).

## Stack

- Python 3.12+ (entorno local con 3.13, sin features exclusivas de 3.13/3.14).
- FastAPI + Pydantic v2 + SQLAlchemy 2.0 (`Mapped[]`, estilo declarativo moderno) + Alembic.
- Driver **psycopg 3**, sesión **síncrona** (`postgresql+psycopg://`). Nada de async/asyncpg.
- GeoAlchemy2 para `Relevamiento.ubicacion` (`geography(Point, 4326)`), sujeto a que PostGIS esté
  habilitado en Neon (verificar antes de asumir).
- Tests: pytest + httpx + `TestClient`.
- Config: `pydantic-settings`, todo por variables de entorno. Nunca credenciales en el repo.

## Comandos

```bash
python -m venv .venv
.venv/Scripts/activate          # Windows
pip install -r requirements.txt

uvicorn app.main:app --reload   # correr local

alembic upgrade head             # aplicar migraciones (nunca automático en el arranque)
alembic revision -m "mensaje"    # nueva migración manual (no --autogenerate a ciegas: revisar diff)

pytest                           # correr tests
```

## Estructura

```
app/
  main.py               app factory, routers, middlewares, exception handlers
  core/                 config (pydantic-settings), autorización stub (get_current_user, require_rol)
  db/                   engine, session, base declarativa
  models/               modelos SQLAlchemy — espejo exacto de schema.sql, no inventar columnas
  schemas/              Pydantic v2, request y response separados, alias camelCase
  api/                  routers: relevamientos, especies, puntos, reglamentacion, indicadores, export
  services/             lógica de negocio (duplicados, solapamiento, cálculo de indicadores)
  repositories/         acceso a datos / queries SQLAlchemy
alembic/
tests/
```

Los routers **no hablan con la base**: llaman a `services`, que usan `repositories`. No saltear esta
capa "porque es más rápido".

## Reglas de estilo y convenciones del proyecto

- **JSON en camelCase, columnas en snake_case** (con dos excepciones ya existentes en el schema:
  `Reglamentacion.fechaInicio` / `fechaFin` están en camelCase en la base — no tocar, no "corregir").
  Resolver el mapeo con el alias generator de Pydantic (`alias_generator=to_camel` +
  `populate_by_name=True`), no campo por campo.
- Prefijo de rutas `/api`, sin versión.
- Formato de error único en toda la API:
  `{"error": {"codigo": "...", "mensaje": "...", "detalles": [...]}}`, vía exception handlers
  globales (incluido `RequestValidationError`). Códigos en uso: `RECURSO_NO_ENCONTRADO` (404),
  `ERROR_VALIDACION` (422), `CONFLICTO` (409), `ERROR_INTERNO` (500).
- Timestamps ISO 8601 con offset (`-03:00`). Paginación `page` (base 0) / `size` (default 20, máx
  100), respuesta `{items, page, size, total}`.
- Exportación CSV la genera el backend (`StreamingResponse`, UTF-8 con BOM), nunca la web.
- **No hay fotos**: ni columna, ni storage, ni campo en request/response. No mencionar.
- **Fiscalizador y Pescador son entidades distintas**, no unificar.
- Duplicados de relevamiento: se resuelven con la constraint
  `UNIQUE(fecha_hora, id_pescador, id_fiscalizador)` vía `ON CONFLICT` o `try/except IntegrityError`
  con rollback limpio — **nunca** un `SELECT` previo (condición de carrera) ni un 500 crudo.
- **Ninguna búsqueda ni referencia externa (web, móvil, o cualquier cliente de la API) usa el `id`
  interno de `Punto_desembarco`, `Pescador`, `Fiscalizador` ni `Especie_Pescado`**: esos `id` son
  correlativos generados por el motor de la base, sin significado de negocio. Toda referencia a
  esas entidades —filtros de búsqueda, body de creación— viaja por su columna `UNIQUE` (clave de
  negocio) y el backend la resuelve al `id` interno solo puertas adentro (repositories/services).
  Aplica a: `puntoDesembarco` (nombre), `nroPescador` (`Pescador.nro_pescador`), `fiscalizador`
  (`Fiscalizador.nombre_user`) y `especie` (`Especie_Pescado.nombre_especie`). Las respuestas sí
  pueden incluir el `id` interno junto al campo de negocio (es solo informativo), pero nunca se
  acepta como criterio de búsqueda o de referencia en un request.
- `puntoDesembarco` en `POST /api/relevamientos` viaja como **nombre en texto** (no id), se resuelve
  contra `Punto_desembarco.nombre` (columna `UNIQUE`).
- `fiscalizador` (username, `Fiscalizador.nombre_user`) va en el body del POST de relevamientos como
  campo **temporal**, con comentario explícito de que se reemplaza por el usuario del token cuando
  exista auth real. Antes viajaba como `fiscalizadorId` (id interno) — se cambió a la clave de
  negocio por la misma regla de arriba.
- Reglas de veda: `talla_min`/`talla_max` son `NOT NULL`; cuando `en_veda = true` se guardan
  `talla_min = 0` / `talla_max = 9999` (default aplicado en el backend). Se exponen siempre como
  números en el JSON, nunca `null`. El campo JSON es `veda` (alias de `en_veda`), no `enVeda`.
  La validación de negocio mira **solo** `en_veda`, ignora tallas si está en veda.
- Indicadores: siempre agregaciones SQL (`GROUP BY`, `date_trunc`), nunca traer filas a Python.
  `capturas-por-punto` usa LEFT JOIN desde `Punto_desembarco` (puntos sin capturas → `cantidad: 0`),
  ordenado por `numero_orden`. `evolucion-temporal` usa un enum validado para `agrupacion`
  (`dia`/`mes`/`anio`), nunca interpolado en SQL crudo, y devuelve serie continua sin huecos.
- Autenticación: no implementada todavía. `get_current_user()` vive aislado en `app/core/`, devuelve
  un usuario stub (rol por env var, default `ADMINISTRADOR`), **claramente marcado como temporal**.
  `require_rol(*roles)` ya se aplica con los roles definitivos (`FISCALIZADOR`, `USUARIO`,
  `ADMINISTRADOR`) aunque hoy no bloquee nada real. `POST /api/auth/login` no se expone.
- No hay filtrado de campos por rol en las respuestas: quien tiene permiso de lectura ve el objeto
  completo.
- No modificar `schema.sql` más allá de lo autorizado en `PLAN.md` sección 3 (identity columns,
  ajuste de `Punto_desembarco`, índices). No crear tablas de usuarios/roles/auditoría/dispositivos.
- Nada de Docker Compose, Redis, Celery, WebSockets, gráficos/PDFs generados en el backend.

## Seeds pendientes

Las listas reales de especies y puntos de desembarco todavía no existen (ver PLAN.md). El script de
seed (`alembic` o `scripts/seed.py`) queda con listas vacías/parametrizadas hasta recibirlas — no
inventar datos de ejemplo como si fueran reales.

## Flujo de trabajo

Fase por fase (ver PLAN.md sección "Fases"), un commit por fase, tests de esa fase pasando antes de
avanzar. No adelantar fases ni mezclar commits de fases distintas.
