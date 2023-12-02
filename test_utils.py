from datetime import datetime

import pytz


def datetime_from_str(s: str):
    # assign UTC timezone, do not move clock
    return pytz.UTC.localize(datetime.strptime(s, "%Y-%m-%d %H:%M"))
