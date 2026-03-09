from datetime import datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

def get_local_time():
    """Return the current time in the configured timezone."""
    return datetime.now(ZoneInfo(settings.DEFAULT_TIMEZONE))
