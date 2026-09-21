from datetime import date

from sqlalchemy import Date, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Reglamentacion(Base):
    __tablename__ = "Reglamentacion"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    # Columnas físicamente en camelCase en la base (particularidad de schema.sql, no se corrige).
    fecha_inicio: Mapped[date] = mapped_column("fechaInicio", Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column("fechaFin", Date, nullable=True)

    reglas = relationship("Regla", back_populates="reglamentacion")
