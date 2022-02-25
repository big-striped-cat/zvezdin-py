from datetime import datetime
from typing import Optional

import pytz


class Logger:
    def __init__(self, tz: Optional[pytz.BaseTzInfo] = None):
        self._tz = tz

    def format_datetime(self, dt: datetime) -> str:
        tz = self._tz or pytz.UTC
        return dt.astimezone(tz).strftime('%Y-%m-%d %H:%M')

    def log(self, s: str):
        print(s)

    def debug(self, s: str):
        pass
