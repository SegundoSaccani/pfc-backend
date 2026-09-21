from sqlalchemy import Identity, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PuntoDesembarco(Base):
    """Forma posterior a la migración 0002 (ver PLAN.md sección 2.1 / 3): se reemplaza
    `nro_identificacion` por `numero_orden` y se agrega UNIQUE(nombre)."""

    __tablename__ = "Punto_desembarco"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    numero_orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
