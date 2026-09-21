from sqlalchemy import Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EspeciePescado(Base):
    __tablename__ = "Especie_Pescado"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nombre_especie: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
