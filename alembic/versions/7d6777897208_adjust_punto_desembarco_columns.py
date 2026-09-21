"""adjust punto_desembarco columns

Revision ID: 7d6777897208
Revises: 4de0ce8d8f9a
Create Date: 2026-09-15 12:23:11.702940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d6777897208'
down_revision: Union[str, None] = '4de0ce8d8f9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PLAN.md sección 2.1 / 3.3: la tabla ya existe con "nro_identificacion" (BIGINT NOT NULL) y sin
# UNIQUE en "nombre". La forma pedida es id / nombre (UNIQUE) / numero_orden (INTEGER). Se asume
# sin datos de producción a preservar (confirmado). numero_orden queda nullable hasta cargar los
# seeds reales (PLAN.md sección 6) — pasar a NOT NULL en una migración futura una vez poblada.


def upgrade() -> None:
    op.drop_column("Punto_desembarco", "nro_identificacion")
    op.add_column("Punto_desembarco", sa.Column("numero_orden", sa.Integer(), nullable=True))
    op.create_unique_constraint(
        "punto_desembarco_nombre_unique", "Punto_desembarco", ["nombre"]
    )


def downgrade() -> None:
    op.drop_constraint("punto_desembarco_nombre_unique", "Punto_desembarco", type_="unique")
    op.drop_column("Punto_desembarco", "numero_orden")
    op.add_column(
        "Punto_desembarco", sa.Column("nro_identificacion", sa.BigInteger(), nullable=False)
    )
