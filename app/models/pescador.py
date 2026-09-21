from sqlalchemy import BigInteger, Identity
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Pescador(Base):
    __tablename__ = "Pescador"

    id: Mapped[int] = mapped_column(Identity(always=False), primary_key=True)
    nro_pescador: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
