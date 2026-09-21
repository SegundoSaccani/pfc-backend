# Arquitectura del backend — Relevamiento de Pesca Artesanal

Este documento explica cómo está armado el proyecto: primero la estructura de carpetas y qué
responsabilidad tiene cada módulo, y después, archivo por archivo, qué hace cada `.py`. Es un
mapa de navegación del código, no reemplaza a [PLAN.md](../PLAN.md) (decisiones y contexto del
proyecto) ni a [schema.sql](../schema.sql) / [api_spec.txt](../api_spec.txt) (fuente de verdad de
la base y del contrato HTTP).

## Idea general

Es una API FastAPI que expone en `/api/*` los datos de relevamientos de pesca artesanal, para dos
clientes: una app móvil (fiscalizadores que cargan relevamientos en el momento) y una web
(investigadores/Ministerio que consultan y exportan). El flujo de una request siempre es:

```
router (app/api) → service (app/services) → repository (app/repositories) → model (app/models) → DB
```

Los routers nunca hablan directo con SQLAlchemy: arman filtros a partir de query params y delegan
en `services`. Los `services` contienen las reglas de negocio (validaciones, duplicados,
solapamientos, mapeo a schemas de respuesta) y usan `repositories` para las queries. Los
`repositories` son la única capa que escribe SQL/SQLAlchemy Core u ORM contra los `models`.

---

## 1. Estructura de carpetas

```
app/
  core/          configuración, autorización stub, manejo de errores, utilidades chicas
  db/            engine, sesión, base declarativa, datos de seed
  models/        modelos SQLAlchemy — espejo de schema.sql
  schemas/       Pydantic v2 — contratos request/response de la API (JSON camelCase)
  api/           routers FastAPI — un archivo por recurso
  services/      lógica de negocio + mappers modelo→schema
  repositories/  acceso a datos (SQLAlchemy) por recurso
alembic/         migraciones (versiones incrementales sobre schema.sql)
scripts/         scripts de operación (seed)
tests/           pytest + TestClient
```

### `app/core/` — configuración transversal

No depende de ningún otro paquete de `app/` (salvo `app/core` entre sí). Contiene todo lo que es
"infraestructura" del proyecto: settings desde variables de entorno, el stub de autenticación, el
formato único de error, los roles válidos y utilidades de fecha/hora. Todos los demás módulos
importan de acá, nunca al revés.

### `app/db/` — conexión a la base

Engine de SQLAlchemy (driver psycopg 3, sesión síncrona), la `Base` declarativa de la que heredan
los modelos, el generador de sesión (`get_db`, usado como dependencia de FastAPI) y los datos de
seed (hoy vacíos, ver [PLAN.md](../PLAN.md) sección 6).

### `app/models/` — modelos SQLAlchemy

Un archivo por tabla, espejo exacto de `schema.sql`. No se agregan columnas que no estén en la
base. Usan el estilo declarativo moderno de SQLAlchemy 2.0 (`Mapped[]` / `mapped_column`).

### `app/schemas/` — contratos Pydantic

Definen qué entra y qué sale de la API. Todos heredan de `CamelModel` (`app/schemas/base.py`), que
resuelve el mapeo snake_case (Python) ↔ camelCase (JSON) automáticamente. Separan claramente
schemas de request (`*Create`, `*Update`) de los de response (`*Detalle`, `*Resumen`,
`*ListItem`, `*Response`).

### `app/api/` — routers

Un router por recurso (relevamientos, catálogos, reglamentación, indicadores, export, health).
Cada endpoint: recibe query params/body, arma el filtro o payload tipado, llama al `service`
correspondiente y devuelve lo que el service retorna (FastAPI lo serializa con el `response_model`
declarado). La autorización (`require_rol`) se aplica acá, como dependencia de cada endpoint.

### `app/services/` — lógica de negocio

Acá viven las reglas que importan: validación de referencias antes de insertar, manejo de
duplicados y conflictos, cálculo de convenciones (tallas en veda), armado de respuestas agregadas
para indicadores, y generación de CSV. También viven acá los "mappers" que convierten instancias
de modelos SQLAlchemy en instancias de schemas Pydantic de response.

### `app/repositories/` — acceso a datos

Las únicas funciones que arman `select(...)`, `insert(...)`, joins, agregaciones SQL, etc. Reciben
la `Session` y devuelven filas o instancias de modelos — nunca schemas Pydantic ni objetos de
respuesta HTTP. Cada archivo se corresponde con un área del dominio (relevamientos, indicadores,
reglamentaciones); no hay un repositorio por tabla individual.

### `alembic/` — migraciones

Migraciones manuales (no autogeneradas a ciegas) que van ajustando `schema.sql` dentro de lo
autorizado en PLAN.md: identity columns, forma final de `Punto_desembarco`, índices para
indicadores.

### `scripts/` — scripts operativos

Hoy solo `seed.py`, que corre el seed de especies/puntos de desembarco contra la base configurada
en `DATABASE_URL`.

### `tests/` — pruebas

pytest + `httpx` + `TestClient` de FastAPI. Un archivo de test por router/service/repository
relevante, más algunos tests transversales (`test_models.py`, `test_errors.py`, `test_health.py`,
`test_auth.py`).

---

## 2. Archivos, uno por uno

### Raíz del proyecto

- **`CLAUDE.md`** — instrucciones del proyecto para trabajar con Claude Code: stack, estructura,
  reglas de estilo y convenciones que todo el código debe respetar.
- **`PLAN.md`** — contexto completo del proyecto: decisiones tomadas, fases de desarrollo,
  limitaciones conocidas. Es la fuente de verdad de *por qué* el código es como es.
- **`schema.sql`** — el schema real de la base de datos (Postgres/Neon + PostGIS). Los modelos de
  `app/models/` son un espejo de esto; nunca al revés.
- **`api_spec.txt`** — contrato de la API tal como se acordó con los consumidores (móvil/web).
  Referencia para el diseño de `app/schemas/` y `app/api/`.
- **`requirements.txt`** — dependencias fijadas (FastAPI, SQLAlchemy 2.0, psycopg 3, Alembic,
  Pydantic v2 + pydantic-settings, GeoAlchemy2 + Shapely, pytest + httpx).
- **`alembic.ini`** — configuración de Alembic (la URL real de conexión se sobreescribe en
  `alembic/env.py` desde `Settings`, no desde este archivo).
- **`render.yaml`** — configuración de despliegue en Render.
- **`README.md`** — documentación de arranque del proyecto.

### `app/main.py`

Application factory (`create_app()`) que arma la instancia de FastAPI. Responsabilidades:

- Registra los **exception handlers globales** que implementan el formato único de error de la
  API (`{"error": {"codigo", "mensaje", "detalles"}}`):
  - `ApiError` → usa el `status_code`/`codigo`/`mensaje`/`detalles` que trae la excepción
    (`RecursoNoEncontrado`, `ErrorValidacion`, `Conflicto` de `app/core/errors.py`).
  - `StarletteHTTPException` → mapea el `status_code` a un código (`NO_AUTORIZADO`, `PROHIBIDO`,
    `RECURSO_NO_ENCONTRADO`, `CONFLICTO`, `ERROR_VALIDACION`, o `ERROR_INTERNO`/`ERROR_SOLICITUD`
    según el rango) vía el diccionario `_CODIGO_POR_STATUS`.
  - `RequestValidationError` (errores de validación de Pydantic en request) → 422
    `ERROR_VALIDACION` con el detalle de FastAPI serializado.
  - `Exception` genérica (catch-all) → 500 `ERROR_INTERNO`, sin filtrar detalles internos.
- Registra los routers, con un comentario explícito sobre el **orden de inclusión**: `export`
  router va antes que `relevamientos`, porque si no, `/api/relevamientos/export` matchea contra la
  ruta `/api/relevamientos/{relevamiento_id}` y Starlette intenta parsear `"export"` como id
  (rompe con 422 en vez de exportar).
- `app = create_app()` al final: instancia real que usa Uvicorn/tests.

### `app/core/`

- **`config.py`** — `Settings` (pydantic-settings), lee `DATABASE_URL` (obligatoria) y
  `DEFAULT_ROL` (default `ADMINISTRADOR`) desde variables de entorno / `.env`. `settings` es la
  instancia única que importa el resto del código.
- **`auth.py`** — **stub temporal de autorización**, marcado explícitamente como tal en su
  docstring. No hay JWT ni login todavía. `get_current_user()` devuelve un `UsuarioActual` fijo
  (`id=0`, rol de `settings.default_rol`). `require_rol(*roles)` es la dependencia real que ya
  usan los routers con los roles definitivos (`FISCALIZADOR`, `USUARIO`, `ADMINISTRADOR`); hoy no
  bloquea nada real porque siempre hay un usuario stub, pero el día que exista auth real, este es
  el único archivo a reemplazar.
- **`errors.py`** — jerarquía de excepciones de negocio: `ApiError` (base, lleva
  `status_code`/`codigo`/`mensaje`/`detalles`), y sus tres subclases concretas usadas en los
  services: `RecursoNoEncontrado` (404), `ErrorValidacion` (422), `Conflicto` (409). Estas son las
  que capturan los handlers de `main.py`.
- **`roles.py`** — `Rol`, enum de los tres roles del sistema: `ADMINISTRADOR`, `USUARIO`,
  `FISCALIZADOR`.
- **`tz.py`** — zona horaria del proyecto (`America/Argentina/Buenos_Aires`) y `hoy()`, que
  devuelve la fecha actual en esa zona (usada por ejemplo para el nombre de archivo de las
  exportaciones y como default de "fecha vigente" en reglamentación).

### `app/db/`

- **`base.py`** — `Base(DeclarativeBase)`, la clase declarativa de la que heredan todos los
  modelos de `app/models/`.
- **`session.py`** — crea el `engine` de SQLAlchemy contra `settings.database_url`
  (`pool_pre_ping=True`, `pool_size=5`, `max_overflow=0`, y `prepare_threshold=None` en
  `connect_args`: deshabilita prepared statements del lado de psycopg porque Neon usa PgBouncer en
  modo transacción, que no los soporta bien). Define `SessionLocal` (sessionmaker síncrono) y
  `get_db()`, generador usado como dependencia de FastAPI (`Depends(get_db)`) que abre sesión, la
  entrega y la cierra en el `finally`.
- **`seed_data.py`** — `ESPECIES` y `PUNTOS_DESEMBARCO` son listas vacías (todavía no existen los
  datos reales, ver PLAN.md sección 6 — **no se inventan** valores de ejemplo). `seed(session)`
  inserta lo que haya en esas listas, sin duplicar si ya existen (busca por `nombre_especie` /
  `nombre` antes de agregar).

### `app/models/`

Todos siguen el mismo patrón: `__tablename__` igual al nombre real de la tabla (con mayúsculas,
como en `schema.sql`), PK `id` con `Identity(always=False)` (el motor genera el id vía
`GENERATED BY DEFAULT AS IDENTITY`, aplicado en la migración `4de0ce8d8f9a`, pero el backend puede
seguir insertando un id explícito si hiciera falta).

- **`__init__.py`** — reexporta todos los modelos (`EspeciePescado`, `Fiscalizador`,
  `PescadoIndividuo`, `Pescador`, `PuntoDesembarco`, `Regla`, `Reglamentacion`, `Relevamiento`) para
  poder importarlos como `from app.models import X`. También es el módulo que hay que importar
  para que todos los modelos queden registrados en `Base.metadata` (lo usa `alembic/env.py`).
- **`especie_pescado.py`** — tabla `Especie_Pescado`: `id`, `nombre_especie` (único).
- **`fiscalizador.py`** — tabla `Fiscalizador`: `id`, `nombre_user` (único). Entidad separada de
  `Pescador` a propósito (no se unifican, por regla explícita del proyecto).
- **`pescador.py`** — tabla `Pescador`: `id`, `nro_pescador` (único, `BigInteger`).
- **`pescado_individuo.py`** — tabla `Pescado_individuo`: un pez capturado dentro de un
  relevamiento. `talla` (obligatoria), `confianza_especie` (opcional, viene de un modelo de
  identificación automática), FK a `Relevamiento` y a `Especie_Pescado`. Relación `relevamiento`
  (back-populates con `Relevamiento.individuos`) y `especie`.
- **`punto_desembarco.py`** — tabla `Punto_desembarco`: `id`, `nombre` (único), `numero_orden`
  (nullable hasta que se carguen los seeds reales). El docstring aclara que esta es la forma
  *posterior* a la migración `7d6777897208` (se reemplazó `nro_identificacion` por `numero_orden` +
  UNIQUE en `nombre`).
- **`regla.py`** — tabla `Regla`: una regla de veda/talla para una especie dentro de una
  reglamentación. `en_veda` (NOT NULL), `talla_min`/`talla_max` (NOT NULL, ver convención de
  veda en `app/services/reglamentaciones.py`), FKs a `Reglamentacion` y `Especie_Pescado`, con
  `UniqueConstraint(id_reglamentacion, id_especie)` — una sola regla por especie por
  reglamentación. Relaciones `reglamentacion` y `especie`.
- **`reglamentacion.py`** — tabla `Reglamentacion`: período de vigencia (`fecha_inicio` /
  `fecha_fin`, con `fecha_fin` nullable = "sin fin todavía"). Nota importante: las columnas físicas
  en la base están en camelCase (`fechaInicio`, `fechaFin`) — es la única excepción documentada al
  estilo snake_case de la base, y el modelo lo resuelve mapeando el nombre de columna
  explícitamente (`mapped_column("fechaInicio", ...)`) sin "corregirlo". Relación `reglas`
  (back-populates con `Regla.reglamentacion`).
- **`relevamiento.py`** — tabla `Relevamiento`, la entidad central. `fecha_hora` (con timezone),
  `id_punto_desembarco` (nullable), `ubicacion` (`Geography(POINT, 4326)` vía GeoAlchemy2,
  nullable), FKs a `Pescador` y `Fiscalizador`, `observaciones` opcional. Tiene
  `UniqueConstraint(fecha_hora, id_pescador, id_fiscalizador)`, que es la constraint que resuelve
  duplicados (ver `app/repositories/relevamientos.py`). Relaciones a `punto_desembarco`,
  `pescador`, `fiscalizador` e `individuos` (lista de `PescadoIndividuo`).

### `app/schemas/`

- **`base.py`** — `CamelModel`, la clase base de todos los schemas. `alias_generator=to_camel` +
  `populate_by_name=True` resuelven el mapeo snake_case↔camelCase automáticamente (sin tener que
  poner `Field(alias=...)` campo por campo). `from_attributes=True` permite construir el schema
  directamente desde instancias de modelos SQLAlchemy.
- **`comunes.py`** — `Ubicacion` (`latitud`, `longitud`), tipo compartido entre relevamientos.
- **`indicadores.py`** — schemas de los tres indicadores y de exportación:
  - `Agrupacion` (enum `dia`/`mes`/`anio`, usado por `evolucion-temporal`).
  - `IndicadorExportable` (enum de los indicadores que se pueden exportar a CSV).
  - `CapturaPorEspecieItem` / `CapturasPorEspecieResponse` (con `excluidos`, siempre 0 hoy, ver
    comentario en el archivo sobre por qué).
  - `CapturaPorEspecieDesglose` / `CapturaPorPuntoItem` (con `por_especie`, que solo aparece
    cuando no se filtra por `especieId`) / `CapturasPorPuntoResponse`.
  - `EvolucionTemporalItem` (`periodo` como string ya formateado, `cantidad`) /
    `EvolucionTemporalResponse`.
- **`reglamentacion.py`** — `ReglamentacionCreate`/`ReglamentacionResumen`/`ReglamentacionDetalle`,
  `ReglaCreate`/`ReglaUpdate`/`ReglaDetalle`. `ReglaCreate`/`ReglaUpdate` dejan `tallaMinima`/
  `tallaMaxima` opcionales porque solo son obligatorias cuando `veda=false` (la validación real
  vive en el service, no en el schema).
- **`relevamiento.py`** — el módulo con más schemas:
  - `IndividuoCreate` / `RelevamientoCreate` (con `fiscalizadorId` marcado como campo **temporal**
    hasta que exista auth real, y `puntoDesembarco` como nombre en texto, no id).
  - `RelevamientoCreateResponse` (`id`, `estado`: `"REGISTRADO"` o `"DUPLICADO"`).
  - Resúmenes usados en listados/detalle: `EspecieResumen`, `PuntoDesembarcoResumen`,
    `FiscalizadorResumen`, `PescadorResumen`.
  - `RelevamientoListItem` / `RelevamientoListResponse` (paginado: `items`, `page`, `size`,
    `total`).
  - `IndividuoDetalle` / `RelevamientoDetalle` (detalle completo de un relevamiento con sus
    individuos).
- **`__init__.py`** — vacío (los schemas se importan directo desde cada submódulo, no hay
  reexport central).

### `app/api/`

Cada router expone `/api/...`, protegido con `require_rol(...)` en cada endpoint según quién puede
hacer qué operación.

- **`health.py`** — `GET /health` (sin prefijo `/api`, sin autorización). Hace `SELECT 1` contra la
  base; devuelve `{"status": "ok", "db": "ok"}` o 503 si la base no responde. Endpoint de
  monitoreo/liveness.
- **`catalogos.py`** — `GET /api/especies` y `GET /api/puntos-desembarco`. Lectura simple ordenada
  (por nombre / por `numero_orden`), accesible a cualquier rol autenticado. Nota en el código:
  `puntos-desembarco` no devuelve `ubicacion` porque esa tabla no tiene esa columna (diverge a
  propósito del ejemplo de `api_spec.txt`).
- **`relevamientos.py`** — el router del flujo principal:
  - `POST /api/relevamientos` (roles `FISCALIZADOR`/`ADMINISTRADOR`) — crea un relevamiento;
    devuelve 201 si es nuevo o 200 si detectó duplicado (`estado` en el body distingue los dos
    casos).
  - `GET /api/relevamientos` (roles `USUARIO`/`ADMINISTRADOR`) — listado paginado con filtros por
    fecha, especie, punto de desembarco y pescador.
  - `GET /api/relevamientos/{id}` (roles `USUARIO`/`ADMINISTRADOR`) — detalle completo.
- **`reglamentacion.py`** — ABM completo de reglamentaciones y reglas:
  - `GET /api/reglamentacion?fecha=` — la vigente a una fecha (o a hoy si no se pasa fecha),
    accesible a cualquier rol.
  - `GET /api/reglamentaciones` — histórico completo (`USUARIO`/`ADMINISTRADOR`).
  - `POST` / `PUT /api/reglamentaciones/{id}` / `DELETE /api/reglamentaciones/{id}` — solo
    `ADMINISTRADOR`.
  - `POST /api/reglamentaciones/{id}/reglas`, `PUT /api/reglas/{id}`, `DELETE /api/reglas/{id}` —
    solo `ADMINISTRADOR`.
- **`indicadores.py`** — `GET /api/indicadores/capturas-por-especie`,
  `GET /api/indicadores/capturas-por-punto`, `GET /api/indicadores/evolucion-temporal` (esta última
  requiere `agrupacion` como query param obligatorio). Todos con filtros de fecha/especie/punto,
  roles `USUARIO`/`ADMINISTRADOR`. El helper privado `_filtros()` evita repetir el armado de
  `FiltrosIndicador` en cada endpoint.
- **`export.py`** — `GET /api/relevamientos/export` y `GET /api/indicadores/{indicador}/export`,
  ambos devuelven un `StreamingResponse` CSV (mismos roles que lectura: `USUARIO`/
  `ADMINISTRADOR`). El helper `_streaming_csv()` arma la respuesta con
  `Content-Disposition: attachment` y el nombre de archivo que devuelve el service.

### `app/services/`

- **`geo.py`** — conversión entre el schema `Ubicacion` (lat/lon) y el tipo geográfico de
  GeoAlchemy2: `ubicacion_a_geografia()` arma un `WKTElement` `POINT(lon lat)` con SRID 4326 para
  guardar; `geografia_a_ubicacion()` hace el camino inverso al leer (`to_shape` + `punto.y`/
  `punto.x` porque en WKT el orden es lon/lat, no lat/lon).
- **`relevamiento_mappers.py`** — funciones puras que convierten instancias de modelos en
  instancias de schemas de response: `especie_a_resumen`, `punto_a_resumen` (soporta `None`),
  `fiscalizador_a_resumen`, `pescador_a_resumen`, `individuo_a_detalle`,
  `relevamiento_a_list_item` (recibe también `cantidad_individuos` porque ese conteo se calcula
  aparte, no viaja en la relación cargada) y `relevamiento_a_detalle`.
- **`relevamientos.py`** — lógica de negocio de relevamientos:
  - `_validar_referencias()` (privada) — antes de insertar, chequea que existan `pescadorId`,
    `fiscalizadorId`, todas las especies de `individuos`, y resuelve `puntoDesembarco` (nombre) al
    id real; si algo no existe, junta todos los errores en una sola `ErrorValidacion` (422) con un
    `detalle` por campo, en vez de cortar en el primero.
  - `crear_relevamiento()` — arma el dict de valores, delega el insert (con manejo de duplicados)
    al repository, y solo inserta los individuos si el relevamiento es nuevo (si era duplicado, no
    toca los individuos ya guardados). Devuelve `estado="REGISTRADO"` o `"DUPLICADO"`.
  - `listar_relevamientos()` — pagina, arma los `RelevamientoListItem` con el conteo de individuos
    por relevamiento.
  - `obtener_relevamiento_detalle()` — 404 (`RecursoNoEncontrado`) si no existe.
- **`reglamentacion_mappers.py`** — igual que `relevamiento_mappers.py` pero para reglamentación:
  `regla_a_detalle`, `reglamentacion_a_resumen`, `reglamentacion_a_detalle`.
- **`reglamentaciones.py`** — lógica de negocio de reglamentación y reglas:
  - `TALLA_MIN_EN_VEDA = 0.0` / `TALLA_MAX_EN_VEDA = 9999.0` — la convención que se guarda cuando
    `en_veda=true` (las columnas son NOT NULL en la base, así que hay que guardar algo numérico).
  - `_validar_rango_fechas()` — `fechaFin` no puede ser anterior a `fechaInicio`.
  - `_validar_no_solapa()` — usa `repo.existe_solapamiento()` para rechazar con `Conflicto` (409)
    una reglamentación que se superpone en el tiempo con otra existente.
  - `crear_reglamentacion()` / `actualizar_reglamentacion()` / `eliminar_reglamentacion()` /
    `listar_reglamentaciones()` / `obtener_vigente()` (usa `hoy()` como fecha por defecto).
  - `_tallas_segun_convencion_veda()` — si `veda=true`, ignora las tallas recibidas y aplica la
    convención 0/9999; si `veda=false`, exige que `tallaMinima`/`tallaMaxima` vengan en el payload
    (si no, 422).
  - `crear_regla()` / `actualizar_regla()` — validan que la especie exista, aplican la convención
    de tallas, y capturan `IntegrityError` (violación del UNIQUE `id_reglamentacion + id_especie`)
    para convertirlo en `Conflicto` (409) con rollback limpio, nunca un 500 crudo.
  - `eliminar_regla()`.
- **`indicadores.py`** — arma las tres respuestas de indicadores a partir de lo que devuelven las
  queries del repository (tuplas), sin traer filas sueltas a Python para agregarlas acá:
  `capturas_por_especie()`, `capturas_por_punto()` (agrega el desglose por especie solo si no se
  filtró por `especieId`, para no duplicar información) y `evolucion_temporal()` (formatea el
  período según la agrupación usando `_FORMATO_PERIODO`). El campo `excluidos` siempre da 0 hoy
  (documentado: no hay forma de tener una `fecha_hora` inválida en la base con el schema actual).
- **`csv_export.py`** — `generar_csv(filas, encabezados)`: generador que arma un CSV en streaming,
  con BOM UTF-8 al principio (para que Excel lo abra bien acentos incluidos). Nota importante en el
  docstring: `filas` tiene que venir ya materializado en memoria (lista de dicts), no un generador
  que siga leyendo de la sesión de SQLAlchemy, porque `StreamingResponse` itera el body *después*
  de que la sesión de la request ya se cerró.
- **`export.py`** — services de exportación que arman las `filas` (dicts) antes de pasárselas a
  `generar_csv`:
  - `exportar_relevamientos()` — arma cada fila combinando el `RelevamientoListItem` mapeado con
    los datos de ubicación/punto "aplanados" a columnas CSV.
  - `exportar_indicador()` — según el `IndicadorExportable` recibido, llama al service de
    indicadores correspondiente y transforma su respuesta a filas planas con los encabezados
    correctos para ese indicador.

### `app/repositories/`

- **`relevamientos.py`** — acceso a datos de relevamientos:
  - `existe_especie()` / `existe_pescador()` / `existe_fiscalizador()` — chequeos de existencia por
    id, usados por el service para validar referencias.
  - `obtener_punto_desembarco_por_nombre()` — resuelve el nombre de texto que viaja en el POST al
    id real.
  - `insertar_relevamiento_o_duplicado()` — el corazón del manejo de duplicados: hace un
    `INSERT ... ON CONFLICT (constraint=...) DO NOTHING RETURNING id` sobre la constraint
    `relevamiento_fecha_hora_id_pescador_id_fiscalizador_unique`. Si no devuelve fila (ya existía),
    hace un segundo `SELECT` para recuperar el id existente. Importante: el chequeo de "existe" no
    se hace con un `SELECT` previo al insert (evita la condición de carrera que pide evitar
    CLAUDE.md) — el `INSERT ... ON CONFLICT` es atómico, el `SELECT` posterior es solo para poder
    devolver el id cuando el conflicto ya ocurrió.
  - `insertar_individuos()` — insert masivo (bulk) de `Pescado_individuo` para un relevamiento.
  - `obtener_detalle()` — trae un relevamiento con todas sus relaciones (`joinedload`/
    `selectinload`) para armar el detalle completo en una sola ida a la base (evitar N+1).
  - `FiltrosRelevamiento` (dataclass) — encapsula los filtros de fecha/especie/punto/pescador y
    arma la lista de condiciones SQLAlchemy (`condiciones()`); el filtro por especie usa un
    `EXISTS` correlacionado contra `Pescado_individuo` en vez de traer individuos.
  - `_conteos_individuos()` — cuenta individuos por relevamiento en un solo `GROUP BY` (no N+1).
  - `listar()` — cuenta el total (para paginación) y trae la página pedida con `offset`/`limit`.
  - `listar_para_exportar()` — igual que `listar()` pero sin paginar (la exportación CSV vuelca
    todo lo que matchea los filtros).
- **`reglamentaciones.py`** — acceso a datos de reglamentación/reglas:
  - `FECHA_MAXIMA = date(9999, 12, 31)` — sentinel para tratar `fecha_fin IS NULL` ("sin fin") como
    "infinito" al comparar rangos de solapamiento, sin tener que hacer casos especiales en la
    condición SQL.
  - `existe_solapamiento()` — chequea si una reglamentación (nueva o editada) se superpone con
    alguna existente, comparando rangos `[fecha_inicio, fecha_fin_o_infinito]`.
  - `obtener_vigente()` — trae la reglamentación cuyo rango cubre una fecha dada, con sus reglas y
    especies precargadas.
  - `listar_historico()`, `obtener_por_id()` (con o sin reglas precargadas), `crear()`,
    `eliminar()`, `obtener_regla()`, `crear_regla()`, `eliminar_regla()`.
- **`indicadores.py`** — las queries de agregación de los tres indicadores, siempre con
  `GROUP BY`/`date_trunc` en SQL, nunca trayendo filas a Python para agregar:
  - `FiltrosIndicador` (dataclass) — igual concepto que `FiltrosRelevamiento`, con métodos que
    devuelven distintos subconjuntos de condiciones según a qué tabla/join se apliquen
    (`condiciones_fecha()`, `condiciones_relevamiento()`, `condiciones()` completo con especie).
  - `capturas_por_especie()` — `COUNT` de individuos agrupado por especie.
  - `capturas_por_punto()` — usa `LEFT JOIN` (`outerjoin`) desde `Punto_desembarco` hacia
    `Relevamiento`/`Pescado_individuo`, con los filtros de fecha puestos en el `ON` del join (no en
    el `WHERE`) para que los puntos sin capturas en el período sigan apareciendo con `cantidad: 0`;
    el filtro por `puntoDesembarcoId`, en cambio, sí va en el `WHERE` porque tiene que restringir
    qué puntos se devuelven. Ordenado por `numero_orden`.
  - `capturas_por_punto_desglose_especie()` — la query auxiliar que arma el desglose por especie
    dentro de cada punto (solo se usa cuando no se filtró por especie).
  - `evolucion_temporal()` / `_construir_evolucion_temporal()` / `_rango_evolucion_temporal()` —
    arma una serie continua sin huecos: genera todos los períodos posibles con
    `generate_series(...)` entre el rango pedido (o el rango real de datos si no hay filtro de
    fecha) y hace `LEFT JOIN` contra las capturas agrupadas por `date_trunc`, con `COALESCE(…, 0)`
    para los períodos sin datos. La unidad de agrupación (`day`/`month`/`year`) sale de un
    diccionario fijo (`UNIDAD_SQL`), nunca se interpola texto de usuario directo en el SQL. Las
    fechas se truncan en la zona horaria del proyecto (`America/Argentina/Buenos_Aires`) antes de
    agrupar, para que "un día" coincida con el día calendario local.

### `alembic/`

- **`env.py`** — configuración de entorno de Alembic. Fuerza `sqlalchemy.url` a
  `settings.database_url` (nunca lee la URL de `alembic.ini`), importa `app.models` para que todos
  los modelos queden registrados en `Base.metadata` (necesario para que Alembic pueda comparar
  metadata contra la base si algún día se usa autogenerate), y define el flujo estándar
  online/offline de Alembic.
- **`versions/4de0ce8d8f9a_identity_columns_on_all_primary_keys.py`** — primera migración: agrega
  `GENERATED BY DEFAULT AS IDENTITY` a la columna `id` de todas las tablas (en `schema.sql`
  original las PK eran `BIGINT NOT NULL` sin identity ni default; el backend delega la generación
  de ids al motor).
- **`versions/7d6777897208_adjust_punto_desembarco_columns.py`** — ajusta `Punto_desembarco`:
  elimina `nro_identificacion`, agrega `numero_orden` (nullable, hasta cargar los seeds reales) y
  agrega el constraint único sobre `nombre` (necesario porque `POST /api/relevamientos` resuelve
  `puntoDesembarco` por nombre).
- **`versions/41623a6fca7d_indicator_indexes.py`** — índices que soportan las queries de
  indicadores: `Relevamiento.fecha_hora`, `Relevamiento.id_punto_desembarco`,
  `Pescado_individuo.id_relevamiento`, `Pescado_individuo.id_especie`.

### `scripts/seed.py`

Entry point ejecutable (`python scripts/seed.py`) que abre una sesión contra la base configurada en
`DATABASE_URL` y corre `app.db.seed_data.seed()`. Hoy no inserta nada porque las listas de
`seed_data.py` están vacías.

### `tests/`

- **`conftest.py`** — setea `DATABASE_URL` a un valor dummy *antes* de importar `app.main` (para
  que `Settings()` no falle por falta de env var al correr tests), y define el fixture `client`
  (`TestClient(app)`) que usan el resto de los tests.
- El resto de los archivos (`test_auth.py`, `test_catalogos_router.py`, `test_csv_export.py`,
  `test_errors.py`, `test_export_router.py`, `test_export_service.py`, `test_geo.py`,
  `test_health.py`, `test_indicadores_repository_sql.py`, `test_indicadores_router.py`,
  `test_indicadores_service.py`, `test_models.py`, `test_reglamentacion_router.py`,
  `test_reglamentaciones_service.py`, `test_relevamientos_router.py`,
  `test_relevamientos_service.py`) siguen la misma organización que el código de `app/`: un test
  file por router, por service o por repository, más `test_models.py` (estructura de los modelos)
  y `test_errors.py` (formato único de error).

---

## 3. Cosas para tener siempre presentes al tocar este código

- **No saltear capas**: un router nunca debe importar de `app/repositories` ni hablar con
  `Session` directo; siempre pasa por un `service`.
- **Duplicados de relevamiento** se resuelven con `ON CONFLICT` sobre la constraint única, nunca
  con un `SELECT` previo (condición de carrera).
- **Reglamentación/`en_veda`**: la validación de negocio mira solo `en_veda`; las tallas 0/9999 son
  una convención de almacenamiento, no un valor de negocio real.
- **Indicadores**: siempre agregaciones SQL; si se necesita un nuevo indicador, la lógica de
  agregación va en `app/repositories/indicadores.py`, no en el service ni en Python puro.
- **Autenticación real todavía no existe**: `app/core/auth.py` es un stub que hay que reemplazar
  entero; `fiscalizadorId` en el POST de relevamientos es temporal por el mismo motivo.
