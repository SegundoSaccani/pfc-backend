# API — Relevamiento de Pesca Artesanal

Backend único de datos para la app móvil (fiscalizadores) y la web (investigadores/Ministerio).
Ver [PLAN.md](PLAN.md) para el detalle de fases, migraciones y limitaciones conocidas, y
[CLAUDE.md](CLAUDE.md) para las convenciones del proyecto.

## Correr local

Requiere Python 3.12+ (desarrollado y probado con 3.13).

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

copy .env.example .env            # completar DATABASE_URL con el connection string de Neon
uvicorn app.main:app --reload
```

`GET /health` verifica conectividad a la base y no requiere autenticación.

## Variables de entorno

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Connection string al endpoint **pooled** de Neon, driver psycopg 3: `postgresql+psycopg://user:pass@ep-xxx-pooler.<region>.aws.neon.tech/db?sslmode=require` |
| `DEFAULT_ROL` | Rol que devuelve el stub temporal de autenticación (`app/core/auth.py`, agregado en fase 3). Default `ADMINISTRADOR`. |

Nunca commitear `.env`. `.env.example` documenta el formato esperado.

## Base de datos (Neon)

1. La base ya existe con la estructura de [schema.sql](schema.sql) (fuente de verdad del modelo de
   datos). Si estás levantando una instancia nueva de cero, aplicá `schema.sql` primero (por ejemplo
   desde el editor SQL de Neon, o `psql "$DATABASE_URL" -f schema.sql`).
2. Verificá que la extensión PostGIS esté habilitada (`CREATE EXTENSION IF NOT EXISTS postgis;`) antes
   de aplicar migraciones que dependan de `geography` — ver limitación en PLAN.md, sección 2.7.
3. Corré las migraciones Alembic (los únicos cambios autorizados sobre el schema, ver PLAN.md sección
   3: identity columns, ajuste de `Punto_desembarco`, índices):

   ```bash
   alembic upgrade head
   ```

   Las migraciones **no** se corren automáticamente al levantar la app en Render.

## Seeds

Las listas reales de especies y puntos de desembarco todavía no están definidas (ver PLAN.md,
sección 6). Completar `ESPECIES` y `PUNTOS_DESEMBARCO` en [app/db/seed_data.py](app/db/seed_data.py)
con los datos reales y después correr:

```bash
python scripts/seed.py
```

No se inventan valores de ejemplo mientras esas listas sigan vacías.

## Tests

```bash
pytest
```

## Deploy en Render

1. Conectar el repo en Render como Web Service (usa [render.yaml](render.yaml)).
2. Cargar `DATABASE_URL` como variable de entorno en el dashboard de Render (no va en `render.yaml`
   por ser secreto).
3. Build: `pip install -r requirements.txt`. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
4. Health check path: `/health`.
5. Correr `alembic upgrade head` manualmente (shell de Render o localmente apuntando a la base de
   producción) después de cada deploy que incluya migraciones nuevas — no es parte del start command.

## Estructura del proyecto

Ver [CLAUDE.md](CLAUDE.md).
