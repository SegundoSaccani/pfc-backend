from sqlalchemy import Identity, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Fiscalizador(Base):
    __tablename__ = "Fiscalizador"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nombre_user: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
