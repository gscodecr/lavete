from datetime import datetime
from zoneinfo import ZoneInfo

def get_cr_time():
    """Return the current time in Costa Rica timezone."""
    return datetime.now(ZoneInfo("America/Costa_Rica"))
