from datetime import datetime

import pytz


def format_datetime(dt: datetime) -> str:
    tz = pytz.timezone('Europe/Moscow')
    return dt.astimezone(tz).strftime('%Y-%m-%d %H:%M')
