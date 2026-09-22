# PLAN.md — Backend API relevamiento pesca artesanal

Estado: **fases 1 a 7 implementadas** (scaffolding, migraciones, auth stub, relevamientos,
catálogos/reglamentación, indicadores, exportación CSV). Ver sección 7 para el detalle de qué falta
para cerrar la Fase 8 (verificación contra Neon real).

## 1. Resumen de lectura

Se leyeron `schema.sql` y `api_spec.txt`. El schema ya existe en su forma "vigente" (según la
consigna, no se toca salvo lo autorizado en la sección 5 del prompt). El spec es un contrato en
construcción con secciones marcadas `DEFINIR` / `PENDIENTES` que este documento (y las decisiones
del punto 4 del prompt) resuelven.

## 2. Contradicciones / divergencias detectadas entre `schema.sql`, `api_spec.txt` y el prompt

### 2.1 `Punto_desembarco` ya existe, con una forma distinta a la pedida — **necesito tu decisión**

El prompt (sección 5.2) da a entender que hay que *crear* `Punto_desembarco` y *agregar* la FK desde
`Relevamiento`. En la realidad, `schema.sql` **ya trae**:

```sql
CREATE TABLE "Punto_desembarco"(
    "id" BIGINT NOT NULL,
    "nombre" VARCHAR(255) NOT NULL,        -- sin UNIQUE
    "nro_identificacion" BIGINT NOT NULL   -- no "numero_orden"
);
...
ALTER TABLE "Relevamiento" ADD CONSTRAINT "relevamiento_id_punto_desembarco_foreign"
    FOREIGN KEY("id_punto_desembarco") REFERENCES "Punto_desembarco"("id");
```

Es decir: la tabla y la FK **ya existen**. Lo que falta para llegar a la forma pedida en 5.2
(`id`, `nombre` UNIQUE, `numero_orden` INTEGER) es:

- Agregar `UNIQUE(nombre)`.
- Reemplazar `nro_identificacion` (BIGINT NOT NULL) por `numero_orden` (INTEGER).

**Mi recomendación** (a confirmar): como la tabla no tiene datos de producción todavía, hago
`DROP COLUMN nro_identificacion` + `ADD COLUMN numero_orden INTEGER` + `ADD CONSTRAINT UNIQUE(nombre)`
en una sola migración Alembic. Si `nro_identificacion` ya tiene datos cargados que no puedo perder,
avisame antes de que corra esto contra Neon.

### 2.2 `puntoDesembarco` en el POST: ¿nombre (string) o ID?

`api_spec.txt` muestra el POST de relevamientos con `"puntoDesembarco": "Puerto de Santa Fe"` (un
string, no un ID). El prompt (sección 8.1) dice "validá que ... `puntoDesembarco` existan" usando
el mismo nombre de campo que el spec, y la sección 5.2 agrega `UNIQUE(nombre)` a la tabla — lo cual
solo tiene sentido si el backend resuelve ese string contra `Punto_desembarco.nombre` para obtener el
id. **Voy a implementarlo así**: el body recibe `puntoDesembarco` como nombre de texto, el backend
busca el punto por nombre exacto y si no existe devuelve `422` con detalle. Aviso este criterio acá
por si preferís que sea `puntoDesembarcoId` numérico en su lugar (requeriría acordarlo con el equipo
móvil).

### 2.3 `fiscalizadorId` no está en el ejemplo del POST del spec

El spec no incluye `fiscalizadorId` en el body de `POST /api/relevamientos`. La sección 6 del prompt
exige aceptarlo igual, como campo temporal hasta que exista auth real. Por prioridad de fuentes
(el prompt manda sobre el spec), lo agrego. **Esto es un campo nuevo que hay que acordar con el
equipo móvil** — lo dejo listado en la sección 6 de este plan.

### 2.4 `capturas-por-punto`: desglose por especie no tiene forma definida en el spec

El prompt pide (8.3) que si no se filtra por especie, el indicador incluya desglose por especie
además del total por punto. El ejemplo del spec no contempla esto. Propongo agregar un campo
`porEspecie` (array de `{especieId, nombreEspecie, cantidad}`) dentro de cada item de `datos`,
presente solo cuando no se pasó `especieId`. A confirmar / acordar con la web.

### 2.5 Columnas de `Reglamentacion` ya están en camelCase en la base

`schema.sql` define `"fechaInicio"` y `"fechaFin"` (comillas, camelCase) en vez de snake_case, a
diferencia del resto de las tablas. No es una contradicción que requiera migración — se mapean
directo a los mismos nombres en JSON — pero rompe la convención "columnas en snake_case" mencionada
en la sección 3 del prompt. Lo dejo documentado como particularidad del schema existente, sin
tocarlo (no está autorizado en la sección 5).

### 2.6 Nombre del campo JSON para `en_veda`

El spec usa `"veda": true/false` en la respuesta de reglas. La columna se llama `en_veda`. Expongo
el campo JSON como `veda` (alias explícito), no `enVeda`.

### 2.7 PostGIS: no puedo confirmarlo todavía

No tengo acceso a la base de Neon en esta etapa (no hay `DATABASE_URL` configurada). La verificación
de `CREATE EXTENSION postgis` va a ser el primer paso técnico de la Fase 1. Si no está disponible,
freno ahí y aviso, como pide el prompt — no voy a asumir que está.

### 2.8 `pescador` en el detalle de relevamiento

El ejemplo del spec en `GET /api/relevamientos/{id}` muestra `"pescador": {"id": 145}` (solo id).
La sección 6 del prompt dice que el rol `USUARIO` "lee todo lo relativo a relevamientos, incluido el
pescador" y que no hay filtrado de campos por rol ("ve el objeto completo"). Voy a devolver el
pescador completo: `{"id": 145, "nroPescador": ...}`, no solo el id. Es una ampliación menor sobre el
ejemplo del spec, no un campo nuevo inventado (el dato ya está en la tabla `Pescador`).

## 3. Migraciones Alembic planificadas (fase 2), todas dentro de lo autorizado por la sección 5

1. **Baseline**: revisión inicial que refleja `schema.sql` tal cual está hoy (para que Alembic tenga
   de dónde partir sin recrear nada).
2. **Identity columns**: `ALTER TABLE ... ALTER COLUMN "id" ADD GENERATED BY DEFAULT AS IDENTITY` en
   las 8 tablas (`Especie_Pescado`, `Pescador`, `Pescado_individuo`, `Relevamiento`, `Reglamentacion`,
   `Regla`, `Fiscalizador`, `Punto_desembarco`).
3. **Punto_desembarco**: `DROP COLUMN nro_identificacion`, `ADD COLUMN numero_orden INTEGER`,
   `ADD CONSTRAINT UNIQUE(nombre)` (sujeto a confirmación, ver 2.1). La FK con `Relevamiento` ya
   existe, no hace falta agregarla.
4. **Índices**: `Relevamiento(fecha_hora)`, `Relevamiento(id_punto_desembarco)`,
   `Pescado_individuo(id_relevamiento)`, `Pescado_individuo(id_especie)`.
5. **Seeds**: especies y puntos de desembarco — **necesito que me pases las listas reales** (nombre
   de cada especie; nombre + `numero_orden` de cada punto de desembarco). No las voy a inventar.

No se toca nada más del schema (no hay tablas de usuarios/roles/auditoría/dispositivos/fotos, no hay
columnas de trazabilidad agregadas).

## 4. Endpoints — nombres/campos que agrego más allá del spec cerrado

Para acordar con web/móvil:

- `fiscalizadorId` (temporal) en el body de `POST /api/relevamientos` (sección 2.3).
- `porEspecie` como sub-array opcional en `GET /api/indicadores/capturas-por-punto` (sección 2.4).
- `excluidos` (entero) en los tres endpoints de indicadores: cantidad de relevamientos excluidos del
  cálculo por fecha inválida/incompleta (requisito de la sección 8.3 del prompt). Con el schema
  actual (`fecha_hora` `NOT NULL`, validada como ISO 8601 al ingresar el relevamiento) no hay forma
  de que exista un relevamiento con fecha inválida en la base, así que este valor siempre da `0` —
  se deja el campo por contrato pero es, en la práctica, una limitación conocida (ver sección 5).
- Los endpoints ya listados en la sección 7 del prompt como "a agregar" (`/api/reglamentaciones` ABM,
  `/api/relevamientos/export`, `/api/indicadores/{indicador}/export`, `/health`) — no son invención
  mía, ya vienen especificados ahí, los implemento tal cual.
- Formato de error único, códigos propuestos (a falta de un catálogo cerrado):
  `RECURSO_NO_ENCONTRADO` (404), `ERROR_VALIDACION` (422), `CONFLICTO` (409, duplicados de regla /
  solapamiento de reglamentación), `ERROR_INTERNO` (500 genérico, no debería verse en uso normal).

`POST /api/auth/login` **no se expone** (sección 6 del prompt). Queda como TODO para cuando agregues
las tablas de usuarios.

## 5. Limitaciones conocidas (para la sección 10, Definition of Done)

- No hay soporte de fotos: ni columna, ni storage, ni campo en ningún request/response.
- `Punto_desembarco.numero_orden` queda **nullable** hasta que se carguen los seeds reales (no hay
  forma de poner `NOT NULL` sin datos ni de inventar un orden). Pasar a `NOT NULL` en una migración
  posterior una vez cargados.
- Las migraciones de la Fase 2 (identity, ajuste de `Punto_desembarco`, índices) se validaron con
  `alembic upgrade head --sql` / `alembic downgrade head:base --sql` (generación de SQL sin conectar)
  porque todavía no hay un `DATABASE_URL` real de Neon disponible en este entorno. Falta correrlas
  contra la base real y confirmar que PostGIS está habilitado (sección 2.7) antes de darlas por
  cerradas.
- Fase 4 (relevamientos): la lógica de negocio (validación de referencias, duplicados, mapeo a
  schemas, roles) está cubierta con tests unitarios mockeando la sesión/repositorio, porque no hay
  Postgres real disponible en este entorno (no hay Docker ni credenciales de Neon). Lo que **no**
  está probado end-to-end todavía: el SQL de `ON CONFLICT DO NOTHING` sobre la constraint de
  duplicados, los joins/`selectinload` del repositorio, y el round-trip de `ubicacion`
  (WKT → `geography` → `WKBElement` → lat/lon). Falta correrlo contra la base real antes de dar la
  fase por cerrada de verdad.
- Fase 5 (catálogos/reglamentación): mismo caso — validación de solapamiento, convención de veda y
  el conflicto de regla duplicada están probados con mocks, no contra Postgres real. La verificación
  de solapamiento usa `date(9999, 12, 31)` como sentinel para "sin fin", en vez de comparar contra
  NULL con lógica SQL de tres valores — más simple y menos propenso a errores, pero asumido no
  probado contra la base real todavía.
- `excluidos: 0` siempre, en los tres endpoints de indicadores (ver sección 4): el schema no permite
  fechas inválidas/incompletas en `Relevamiento.fecha_hora` (`NOT NULL`, validada al ingresar), así
  que el requisito de "informar cuántos se excluyeron" no tiene casos reales que contar con esta
  estructura de datos.
- Fase 6 (indicadores): las queries de agregación (incluida la de `evolucion-temporal`, que arma la
  serie continua con `generate_series` + `date_trunc` + `timezone`) se verificaron compilando el SQL
  contra el dialecto de Postgres (`stmt.compile(dialect=postgresql.dialect())`), sin ejecutarlo — no
  hay Postgres real disponible en este entorno. Falta correrlas contra Neon para confirmar la
  semántica real (zero-fill de puntos sin capturas, serie temporal sin huecos, timezone de
  Argentina en `date_trunc`).
- **Permisos de lectura no especificados explícitamente en el prompt** (decisión propia, a
  confirmar): `GET /api/especies` y `GET /api/puntos-desembarco` se dejaron abiertos a los tres
  roles (son catálogos de referencia sin información sensible, los necesitan la app móvil y la web
  por igual). `GET /api/reglamentacion` (vigente) también se dejó abierto a los tres roles, ya que
  la sección 6 del prompt solo dice explícitamente que el fiscalizador la lee, pero no la prohíbe
  para investigador/administrador. `GET /api/reglamentaciones` (listado histórico) se restringió a
  `USUARIO`/`ADMINISTRADOR` porque el spec lo marca como "lo usa la WEB".
- `GET /api/puntos-desembarco` no devuelve `ubicacion` (la tabla no tiene esa columna; el schema no
  la contempla y no está autorizado agregarla). El mapa se arma con `Relevamiento.ubicacion`.
- Las tallas en reglas de veda se devuelven como números (`0` / `9999`), nunca `null`, por la
  convención de la sección 8.2 del prompt — diverge del ejemplo del spec.
- No hay autenticación real ni ABM de usuarios en esta etapa; `get_current_user()` es un stub por env
  var, claramente marcado como temporal en `app/core/`.
- `fiscalizadorId` viaja en el body del POST de relevamientos en vez de salir del token, hasta que
  exista auth.
- El filtrado de campos por rol en las respuestas de relevamientos no se implementa (por diseño,
  sección 6 del prompt): quien tiene permiso de lectura ve el objeto completo.
- Depende de que PostGIS esté habilitado en la instancia de Neon (a verificar en Fase 1, sin
  asumirlo).

## 6. Decisiones confirmadas (2026-09-15)

1. **2.1** — confirmado: reemplazo `nro_identificacion` por `numero_orden` en `Punto_desembarco`,
   sin preservar datos (tabla sin datos de producción).
2. **2.2** — confirmado: `puntoDesembarco` en el POST viaja como nombre (string), se resuelve contra
   `Punto_desembarco.nombre`.
3. **2.3** — confirmado: se agrega `fiscalizadorId` (temporal) al body del POST, marcado en el código
   para reemplazar por el usuario del token cuando exista auth.
4. **Seeds pendientes**: todavía no hay listas reales de especies ni puntos de desembarco. Se dejó
   `app/db/seed_data.py` con listas `ESPECIES = []` / `PUNTOS_DESEMBARCO = []` a completar, más
   `scripts/seed.py` para correrlo (`python scripts/seed.py`), documentado en el README como paso
   pendiente antes de poder usar el sistema con datos reales. No se inventan valores.
5. **Fase 1** — confirmado, se arranca con el scaffolding.

Plan aprobado. Se continúa con `CLAUDE.md` y la Fase 1.

### 6.1 Decisión (2026-09-22): ninguna búsqueda/referencia externa usa el `id` interno de catálogos

Se detectó que varios endpoints usaban el `id` (PK numérica, sin lógica de negocio, generada por el
motor) de `Punto_desembarco`, `Pescador`, `Fiscalizador` y `Especie_Pescado` como criterio de
búsqueda o de referencia en requests — algo que las columnas `UNIQUE` de esas tablas ya estaban
para resolver. Se corrigió en todos lados, lectura y creación (confirmado con el dueño del
proyecto):

- `GET /api/relevamientos`, `/api/indicadores/*` y sus `/export`: los filtros pasan de
  `especieId`/`puntoDesembarcoId`/`pescadorId` (int) a `especie` (nombre), `puntoDesembarco`
  (nombre) y `nroPescador` (`Pescador.nro_pescador`).
- `POST /api/relevamientos`: `pescadorId` → `nroPescador`; `fiscalizadorId` → `fiscalizador`
  (`Fiscalizador.nombre_user`, sigue siendo el campo temporal sin auth real — ver sección 2.3);
  `individuos[].especieId` → `individuos[].especie` (nombre de especie).
- `POST/PUT /api/reglamentaciones/{id}/reglas` y `/api/reglas/{id}`: `especieId` → `especie`
  (nombre de especie).

Las respuestas no cambian: siguen devolviendo el `id` interno junto al campo de negocio (es solo
informativo, ver `EspecieResumen`/`PescadorResumen`/`FiscalizadorResumen`/`PuntoDesembarcoResumen`),
pero ya no se acepta como entrada en ningún filtro ni body. Regla general documentada en
`CLAUDE.md`. Rompe el contrato con `api_spec.txt` (que mostraba `especieId`/`puntoDesembarcoId`/
`pescadorId`/`fiscalizadorId` numéricos) — divergencia intencional, no se corrige `api_spec.txt`
(es el documento de partida, no un contrato vivo). A coordinar con el equipo móvil/web antes de
integrar.

## 7. Estado de la Fase 8 (tests, OpenAPI, deploy) y qué falta para cerrar el proyecto

Implementado:

- Los 66+ tests (`pytest`) cubren, por endpoint, al menos un happy path y un caso de error: POST
  duplicado (`REGISTRADO`/`DUPLICADO`), referencias inexistentes (422), búsqueda de relevamientos sin
  resultados (`items: []`, `total: 0`), detalle 404, puntos de desembarco con cero capturas en
  `capturas-por-punto`, serie temporal con períodos en cero, solapamiento de reglamentaciones (409),
  regla duplicada por especie (409), convención de veda (tallas 0/9999 ignorando lo enviado), permisos
  por rol (403) en cada endpoint que corresponde, y el round-trip de `ubicacion` (lat/lon → WKT →
  `geography` → `WKBElement` → lat/lon) probado sin necesitar Postgres real.
- El OpenAPI generado (`/docs`) se verificó a mano contra `api_spec.txt`: nombres de rutas y de campos
  coinciden, incluidas las divergencias documentadas (`ubicacion` ausente en puntos de desembarco,
  tallas numéricas en veda, `POST /api/auth/login` no expuesto) y los campos agregados (`excluidos`,
  `porEspecie`, `fiscalizadorId`).
- README con pasos de instalación local, variables de entorno, migraciones y deploy en Render ya
  escrito desde la Fase 1 y actualizado con la ruta real del script de seed.

**Lo que falta y no se puede completar sin acceso a la base real** (no hay Neon ni Docker/Postgres
local en este entorno de desarrollo):

- Correr `alembic upgrade head` contra una Neon real partiendo de `schema.sql` y confirmar que las
  tres migraciones (identity, `Punto_desembarco`, índices) aplican limpio.
- Confirmar que `CREATE EXTENSION postgis` está disponible (sección 2.7) antes de asumir que
  `Relevamiento.ubicacion` funciona como `geography(Point, 4326)`.
- Ejecutar los endpoints end-to-end (no mockeados) para validar la semántica real de: `ON CONFLICT
  DO NOTHING` sobre la constraint de duplicados, los joins/`selectinload` de relevamientos y
  reglamentaciones, y sobre todo la query de `evolucion-temporal` (`generate_series` + `date_trunc` +
  `timezone`), que solo se verificó compilando el SQL, no ejecutándolo.
- Cargar las listas reales de especies y puntos de desembarco y correr `scripts/seed.py`.

En cuanto haya un `DATABASE_URL` de Neon disponible, el siguiente paso es correr toda la suite de
tests de integración pendiente (no incluida todavía porque requeriría mockear cada vez menos y
depender de una base real) y `alembic upgrade head` contra esa instancia.
