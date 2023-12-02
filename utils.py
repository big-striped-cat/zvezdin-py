from datetime import datetime

import pytz

from config import configs


def format_datetime(dt: datetime) -> str:
    tz = pytz.timezone(configs["tz"])
    return dt.astimezone(tz).strftime("%Y-%m-%d %H:%M")
