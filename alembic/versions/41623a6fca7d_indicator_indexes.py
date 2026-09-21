"""indicator indexes

Revision ID: 41623a6fca7d
Revises: 7d6777897208
Create Date: 2026-09-15 12:23:12.193619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '41623a6fca7d'
down_revision: Union[str, None] = '7d6777897208'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# PLAN.md sección 3.4 — índices que soportan los indicadores (búsquedas/agregaciones por fecha,
# punto de desembarco y especie).


def upgrade() -> None:
    op.create_index("ix_relevamiento_fecha_hora", "Relevamiento", ["fecha_hora"])
    op.create_index(
        "ix_relevamiento_id_punto_desembarco", "Relevamiento", ["id_punto_desembarco"]
    )
    op.create_index(
        "ix_pescado_individuo_id_relevamiento", "Pescado_individuo", ["id_relevamiento"]
    )
    op.create_index("ix_pescado_individuo_id_especie", "Pescado_individuo", ["id_especie"])


def downgrade() -> None:
    op.drop_index("ix_pescado_individuo_id_especie", table_name="Pescado_individuo")
    op.drop_index("ix_pescado_individuo_id_relevamiento", table_name="Pescado_individuo")
    op.drop_index("ix_relevamiento_id_punto_desembarco", table_name="Relevamiento")
    op.drop_index("ix_relevamiento_fecha_hora", table_name="Relevamiento")
