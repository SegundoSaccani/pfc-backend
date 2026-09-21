"""Corre el seed de especies y puntos de desembarco contra la base configurada en DATABASE_URL.

Uso: python scripts/seed.py
"""

from app.db.seed_data import seed
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal() as session:
        seed(session)


if __name__ == "__main__":
    main()
