# Referencia de la API — formatos y campos

Este documento describe, endpoint por endpoint, qué espera recibir la API (query params / body) y
qué devuelve (response), con los campos tal como viajan en JSON (camelCase). Es la foto actual del
código (`app/api/`, `app/schemas/`); para el *por qué* de cada decisión ver [PLAN.md](../PLAN.md) y
[CLAUDE.md](../CLAUDE.md). No reemplaza a [api_spec.txt](../api_spec.txt) (el contrato original
propuesto) sino que documenta el contrato **real e implementado**, que ya diverge de ese archivo en
varios puntos (están marcados como `(diverge de api_spec.txt)` donde aplica).

## Convenciones generales

- **Prefijo**: todas las rutas van bajo `/api`, sin versión — excepto `GET /health`.
- **JSON**: siempre camelCase. Internamente el código usa snake_case; el mapeo es automático
  (`CamelModel`, alias generator), no campo por campo.
- **Fechas/horas**: `fechaHora` es timestamp ISO 8601 **con offset** (ej. `2026-09-13T18:30:00-03:00`).
  Los parámetros `fechaDesde`/`fechaHasta` son fechas simples (`YYYY-MM-DD`, sin hora).
- **Paginación** (donde aplica): query params `page` (base 0, default `0`) y `size` (default `20`,
  máx `100`). Response: `{ "items": [...], "page": ..., "size": ..., "total": ... }`.
- **Claves de negocio, nunca id interno**: ninguna búsqueda ni referencia externa (filtros de
  lectura o campos de un body) acepta el `id` interno (PK numérica, generada por el motor, sin
  significado de negocio) de `Punto_desembarco`, `Pescador`, `Fiscalizador` ni `Especie_Pescado`.
  Se usa siempre la columna `UNIQUE` de esa tabla:
  | Entidad | Se busca/referencia por | Campo JSON |
  |---|---|---|
  | Especie | `nombre_especie` | `especie` |
  | Punto de desembarco | `nombre` | `puntoDesembarco` |
  | Pescador | `nro_pescador` | `nroPescador` |
  | Fiscalizador | `nombre_user` (username) | `fiscalizador` |

  El `id` interno de esas entidades sí puede aparecer en las **respuestas** (junto al campo de
  negocio, a modo informativo, ej. `{"id": 1, "nombre": "Sábalo"}`), pero nunca es válido como
  entrada en un filtro o un body.
- **Autenticación**: no implementada todavía (`app/core/auth.py`, stub temporal). No hay
  `POST /api/auth/login`. El rol efectivo de todas las requests sale de la variable de entorno
  `DEFAULT_ROL` (default `ADMINISTRADOR`), no de un token. Los tres roles ya definidos y aplicados
  con `require_rol(...)` son `FISCALIZADOR`, `USUARIO`, `ADMINISTRADOR`.
- **CSV** (exportaciones): generado por el backend, UTF-8 con BOM, streaming
  (`Content-Disposition: attachment`).

## Formato de error (todas las respuestas de error)

```json
{
  "error": {
    "codigo": "ERROR_VALIDACION",
    "mensaje": "Hay referencias inválidas en el relevamiento.",
    "detalles": [
      { "campo": "nroPescador", "mensaje": "No existe el pescador con nro_pescador 999." }
    ]
  }
}
```

| Código | HTTP | Cuándo |
|---|---|---|
| `RECURSO_NO_ENCONTRADO` | 404 | El recurso pedido no existe |
| `ERROR_VALIDACION` | 422 | Body/query inválido, o referencias inexistentes en el payload |
| `CONFLICTO` | 409 | Duplicado (regla) o solapamiento (reglamentación) |
| `NO_AUTORIZADO` | 401 | (reservado, no se emite hoy — no hay auth real) |
| `PROHIBIDO` | 403 | El rol actual no tiene permiso para ese endpoint |
| `ERROR_INTERNO` | 500 | Error no controlado |
| `ERROR_SOLICITUD` | 4xx genérico | Otro error HTTP sin código específico |

`detalles` es siempre una lista (puede venir vacía) de `{ "campo": ..., "mensaje": ... }`, o el
detalle de validación de FastAPI/Pydantic cuando el error es `RequestValidationError`.

---

## Relevamientos

### `POST /api/relevamientos`

Roles: `FISCALIZADOR`, `ADMINISTRADOR`. Lo usa la app móvil para sincronizar un relevamiento.

**Request body:**

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `fechaHora` | string (ISO 8601 con offset) | sí | Momento del relevamiento |
| `puntoDesembarco` | string \| null | no | Nombre del punto (`Punto_desembarco.nombre`), no id |
| `ubicacion` | `{ "latitud": float, "longitud": float }` \| null | no | Coordenadas del relevamiento |
| `observaciones` | string \| null | no | Texto libre |
| `nroPescador` | int | sí | `Pescador.nro_pescador` (clave de negocio, no id interno) |
| `fiscalizador` | string | sí | `Fiscalizador.nombre_user` (username). **Campo temporal**: hasta que exista auth real, lo manda la app en el body; el día que haya login, sale del token, no del body |
| `individuos` | array | sí (puede ser `[]`) | Lista de peces capturados |
| `individuos[].especie` | string | sí | `Especie_Pescado.nombre_especie`, no id |
| `individuos[].talla` | float | sí | |
| `individuos[].confianzaEspecie` | float \| null | no | Confianza del modelo de identificación automática |

**Response:** `201` si se creó, `200` si ya existía (mismo `fechaHora` + pescador + fiscalizador →
duplicado, no reinserta individuos):

```json
{ "id": 125, "estado": "REGISTRADO" }
```

`estado` es `"REGISTRADO"` o `"DUPLICADO"`.

**Errores:** `422 ERROR_VALIDACION` con un `detalle` por cada referencia inválida (se acumulan
todas, no corta en la primera): `campo` puede ser `nroPescador`, `fiscalizador`,
`individuos.especie` o `puntoDesembarco`. `403 PROHIBIDO` si el rol no es `FISCALIZADOR`/`ADMINISTRADOR`.

### `GET /api/relevamientos`

Roles: `USUARIO`, `ADMINISTRADOR`. Lo usa la web.

**Query params** (todos opcionales salvo paginación):

| Param | Tipo | Descripción |
|---|---|---|
| `fechaDesde` | date | Filtra `fechaHora >= fechaDesde` |
| `fechaHasta` | date | Filtra `fechaHora < fechaHasta + 1 día` (incluye todo ese día) |
| `especie` | string | Nombre de especie — trae relevamientos que capturaron esa especie |
| `puntoDesembarco` | string | Nombre del punto de desembarco |
| `nroPescador` | int | `Pescador.nro_pescador` |
| `page` | int | Default `0` |
| `size` | int | Default `20`, máx `100` |

**Response:**

```json
{
  "items": [
    {
      "id": 125,
      "fechaHora": "2026-09-13T18:30:00-03:00",
      "puntoDesembarco": { "id": 3, "nombre": "Puerto de Santa Fe" },
      "ubicacion": { "latitud": -31.633, "longitud": -60.699 },
      "fiscalizador": { "id": 4, "nombreUsuario": "fiscalizador1" },
      "cantidadIndividuos": 2
    }
  ],
  "page": 0,
  "size": 20,
  "total": 128
}
```

`puntoDesembarco` y `ubicacion` pueden ser `null`.

### `GET /api/relevamientos/{id}`

Roles: `USUARIO`, `ADMINISTRADOR`. Detalle completo (incluye pescador e individuos; no hay
filtrado de campos por rol).

**Response:**

```json
{
  "id": 125,
  "fechaHora": "2026-09-13T18:30:00-03:00",
  "puntoDesembarco": { "id": 3, "nombre": "Puerto de Santa Fe" },
  "ubicacion": { "latitud": -31.633, "longitud": -60.699 },
  "observaciones": "Sin observaciones",
  "fiscalizador": { "id": 4, "nombreUsuario": "fiscalizador1" },
  "pescador": { "id": 145, "nroPescador": 145 },
  "individuos": [
    {
      "id": 501,
      "especie": { "id": 1, "nombre": "Sábalo" },
      "talla": 42.5,
      "confianzaEspecie": null
    }
  ]
}
```

**Errores:** `404 RECURSO_NO_ENCONTRADO` si no existe.

### `GET /api/relevamientos/export`

Roles: `USUARIO`, `ADMINISTRADOR`. Mismos query params que `GET /api/relevamientos` salvo
paginación (`fechaDesde`, `fechaHasta`, `especie`, `puntoDesembarco`, `nroPescador`). Devuelve un
CSV (`text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="relevamientos_YYYY-MM-DD.csv"`)
con columnas: `id`, `fechaHora`, `puntoDesembarcoId`, `puntoDesembarco`, `latitud`, `longitud`,
`fiscalizadorId`, `fiscalizador`, `cantidadIndividuos`. (El CSV sí incluye los `id` internos como
columnas informativas adicionales, junto al nombre — no son un criterio de filtro.)

---

## Catálogos

### `GET /api/especies`

Roles: cualquiera (`FISCALIZADOR`, `USUARIO`, `ADMINISTRADOR`). Sin query params.

```json
[
  { "id": 1, "nombre": "Sábalo" },
  { "id": 2, "nombre": "Surubí" }
]
```

Ordenado por `nombre_especie`.

### `GET /api/puntos-desembarco`

Roles: cualquiera. Sin query params.

```json
[
  { "id": 1, "nombre": "Puerto de Santa Fe" }
]
```

Ordenado por `numero_orden` (no se expone en la response). **No incluye `ubicacion`** (diverge de
`api_spec.txt`): la tabla no tiene esa columna; el mapa se arma con `Relevamiento.ubicacion`.

---

## Reglamentación

### `GET /api/reglamentacion`

Roles: cualquiera. Devuelve la reglamentación vigente.

**Query params:** `fecha` (date, opcional — default hoy en zona horaria Argentina).

```json
{
  "id": 4,
  "fechaInicio": "2026-01-01",
  "fechaFin": null,
  "reglas": [
    {
      "id": 15,
      "especie": { "id": 1, "nombre": "Sábalo" },
      "tallaMinima": 42.0,
      "tallaMaxima": 9999.0,
      "veda": false
    }
  ]
}
```

Nota: `tallaMinima`/`tallaMaxima` **siempre** vienen como número (nunca `null`) — cuando
`veda: true` se guarda la convención `0` / `9999`, sin importar lo que se haya mandado al crear la
regla (diverge del ejemplo de `api_spec.txt`, que mostraba `null`).

**Errores:** `404 RECURSO_NO_ENCONTRADO` si no hay reglamentación vigente para esa fecha.

### `GET /api/reglamentaciones`

Roles: `USUARIO`, `ADMINISTRADOR`. Histórico completo, sin paginar.

```json
[{ "id": 4, "fechaInicio": "2026-01-01", "fechaFin": null }]
```

### `POST /api/reglamentaciones`

Roles: `ADMINISTRADOR`.

**Body:** `{ "fechaInicio": "2026-01-01", "fechaFin": null }` (`fechaFin` opcional).

**Response:** `201` con el mismo formato de `ReglamentacionDetalle` que `GET /api/reglamentacion`
(con `reglas: []` porque recién se crea).

**Errores:** `422` si `fechaFin < fechaInicio`; `409 CONFLICTO` si se solapa en el tiempo con una
reglamentación existente.

### `PUT /api/reglamentaciones/{id}`

Roles: `ADMINISTRADOR`. Mismo body y validaciones que el `POST`. `404` si no existe.

### `DELETE /api/reglamentaciones/{id}`

Roles: `ADMINISTRADOR`. `204` sin body. `404` si no existe.

### `POST /api/reglamentaciones/{id}/reglas`

Roles: `ADMINISTRADOR`.

**Body:**

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `especie` | string | sí | `Especie_Pescado.nombre_especie`, no id |
| `veda` | bool | sí | |
| `tallaMinima` | float \| null | solo si `veda: false` | Ignorado si `veda: true` |
| `tallaMaxima` | float \| null | solo si `veda: false` | Ignorado si `veda: true` |

Si `veda: true`, el backend guarda `tallaMinima: 0` / `tallaMaxima: 9999` sin importar lo recibido.
Si `veda: false` y falta alguna talla → `422`.

**Response:** `201`:

```json
{ "id": 15, "especie": { "id": 1, "nombre": "Sábalo" }, "tallaMinima": 42.0, "tallaMaxima": 9999.0, "veda": false }
```

**Errores:** `404` si la reglamentación no existe; `422` si la especie no existe o faltan tallas;
`409 CONFLICTO` si ya existe una regla para esa especie en esa reglamentación.

### `PUT /api/reglas/{id}`

Roles: `ADMINISTRADOR`. Mismo body que el `POST` (`especie` opcional: si se omite, no cambia la
especie de la regla). Mismas validaciones/errores. `404` si la regla no existe.

### `DELETE /api/reglas/{id}`

Roles: `ADMINISTRADOR`. `204` sin body. `404` si no existe.

---

## Indicadores

Todos calculados en el backend (agregaciones SQL). Roles: `USUARIO`, `ADMINISTRADOR`.

**Query params comunes** a los tres (todos opcionales): `fechaDesde`, `fechaHasta`, `especie`
(nombre), `puntoDesembarco` (nombre).

### `GET /api/indicadores/capturas-por-especie`

```json
{
  "datos": [
    { "especieId": 1, "nombreEspecie": "Sábalo", "cantidad": 146 },
    { "especieId": 2, "nombreEspecie": "Surubí", "cantidad": 37 }
  ],
  "excluidos": 0
}
```

### `GET /api/indicadores/capturas-por-punto`

```json
{
  "datos": [
    {
      "puntoDesembarcoId": 1,
      "nombre": "Puerto de Santa Fe",
      "cantidad": 210,
      "porEspecie": [{ "especieId": 1, "nombreEspecie": "Sábalo", "cantidad": 150 }]
    },
    { "puntoDesembarcoId": 2, "nombre": "Desvío Arijón", "cantidad": 0, "porEspecie": [] }
  ],
  "excluidos": 0
}
```

Incluye **todos** los puntos de desembarco (aunque tengan `cantidad: 0`), ordenados por
`numero_orden`. `porEspecie` solo aparece (no es `null`) cuando **no** se filtró por `especie`; si
se filtró por especie, `porEspecie` es `null`.

### `GET /api/indicadores/evolucion-temporal`

**Query param adicional obligatorio:** `agrupacion` (`dia` | `mes` | `anio`).

```json
{
  "agrupacion": "mes",
  "datos": [
    { "periodo": "2026-07", "cantidad": 340 },
    { "periodo": "2026-08", "cantidad": 415 }
  ],
  "excluidos": 0
}
```

`periodo` se formatea según `agrupacion`: `YYYY-MM-DD` (día), `YYYY-MM` (mes), `YYYY` (año). La
serie es **continua** (sin huecos): si un período no tuvo capturas, aparece igual con `cantidad: 0`.

**Errores:** `422` si `agrupacion` no es una de las tres válidas.

> `excluidos` está en las tres respuestas por contrato (relevamientos con fecha inválida/incompleta
> excluidos del cálculo), pero siempre da `0` con el schema actual — ver limitación documentada en
> [PLAN.md](../PLAN.md).

### `GET /api/indicadores/{indicador}/export`

Roles: `USUARIO`, `ADMINISTRADOR`. `{indicador}` es uno de `capturas-por-especie`,
`capturas-por-punto`, `evolucion-temporal`. Query params: los comunes de indicadores +
`agrupacion` (solo aplica a `evolucion-temporal`, default `mes`). CSV con columnas según el
indicador:

| Indicador | Columnas CSV |
|---|---|
| `capturas-por-especie` | `especieId`, `nombreEspecie`, `cantidad` |
| `capturas-por-punto` | `puntoDesembarcoId`, `nombre`, `cantidad` |
| `evolucion-temporal` | `periodo`, `cantidad` |

**Errores:** `422` si `{indicador}` no es uno de los tres valores válidos.

---

## Health

### `GET /health`

Sin prefijo `/api`, sin autorización. Chequeo de liveness (`SELECT 1` contra la base).

```json
{ "status": "ok", "db": "ok" }
```

`503` con `{ "status": "error", "db": "unreachable" }` si la base no responde.

---

## Matriz de roles (resumen)

| Endpoint | FISCALIZADOR | USUARIO | ADMINISTRADOR |
|---|---|---|---|
| `POST /api/relevamientos` | ✅ | ❌ | ✅ |
| `GET /api/relevamientos`, `/{id}`, `/export` | ❌ | ✅ | ✅ |
| `GET /api/especies`, `/api/puntos-desembarco` | ✅ | ✅ | ✅ |
| `GET /api/reglamentacion` | ✅ | ✅ | ✅ |
| `GET /api/reglamentaciones` (histórico) | ❌ | ✅ | ✅ |
| ABM de reglamentaciones/reglas | ❌ | ❌ | ✅ |
| `GET /api/indicadores/*` (y `/export`) | ❌ | ✅ | ✅ |
| `GET /health` | — (sin auth) | — | — |
