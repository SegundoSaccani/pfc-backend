from datetime import date, datetime
from zoneinfo import ZoneInfo

ZONA_HORARIA = ZoneInfo("America/Argentina/Buenos_Aires")


def hoy() -> date:
    return datetime.now(ZONA_HORARIA).date()
