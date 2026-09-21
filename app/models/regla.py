from sqlalchemy import BigInteger, Boolean, Double, ForeignKey, Identity, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Regla(Base):
    __tablename__ = "Regla"
    __table_args__ = (
        UniqueConstraint(
            "id_reglamentacion", "id_especie", name="regla_id_reglamentacion_id_especie_unique"
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    en_veda: Mapped[bool] = mapped_column(Boolean, nullable=False)
    talla_min: Mapped[float] = mapped_column(Double, nullable=False)
    talla_max: Mapped[float] = mapped_column(Double, nullable=False)
    id_reglamentacion: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Reglamentacion.id"), nullable=False
    )
    id_especie: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Especie_Pescado.id"), nullable=False
    )

    reglamentacion = relationship("Reglamentacion", back_populates="reglas")
    especie = relationship("EspeciePescado")
