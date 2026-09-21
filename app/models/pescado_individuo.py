from sqlalchemy import BigInteger, Double, ForeignKey, Identity
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PescadoIndividuo(Base):
    __tablename__ = "Pescado_individuo"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    talla: Mapped[float] = mapped_column(Double, nullable=False)
    confianza_especie: Mapped[float | None] = mapped_column(Double, nullable=True)
    id_relevamiento: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Relevamiento.id"), nullable=False
    )
    id_especie: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Especie_Pescado.id"), nullable=False
    )

    relevamiento = relationship("Relevamiento", back_populates="individuos")
    especie = relationship("EspeciePescado")
