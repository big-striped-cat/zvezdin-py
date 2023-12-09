import re
from datetime import timedelta
from typing import Optional


def parse_timedelta(delta: str) -> Optional[timedelta]:
    match = re.match(r"^(\d+)([m|h])$", delta)
    if not match:
        return

    number = int(match.group(1))
    unit = match.group(2)

    if unit == "m":
        return timedelta(minutes=number)
    elif unit == "h":
        return timedelta(hours=number)

    raise RuntimeError("Unknown unit")
