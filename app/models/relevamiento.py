from datetime import datetime

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Relevamiento(Base):
    __tablename__ = "Relevamiento"
    __table_args__ = (
        UniqueConstraint(
            "fecha_hora",
            "id_pescador",
            "id_fiscalizador",
            name="relevamiento_fecha_hora_id_pescador_id_fiscalizador_unique",
        ),
    )

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    fecha_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    id_punto_desembarco: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("Punto_desembarco.id"), nullable=True
    )
    ubicacion: Mapped[WKBElement | None] = mapped_column(
        Geography(geometry_type="POINT", srid=4326), nullable=True
    )
    id_pescador: Mapped[int] = mapped_column(BigInteger, ForeignKey("Pescador.id"), nullable=False)
    id_fiscalizador: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("Fiscalizador.id"), nullable=False
    )
    observaciones: Mapped[str | None] = mapped_column(String(255), nullable=True)

    punto_desembarco = relationship("PuntoDesembarco")
    pescador = relationship("Pescador")
    fiscalizador = relationship("Fiscalizador")
    individuos = relationship("PescadoIndividuo", back_populates="relevamiento")
