import re
from datetime import timedelta
from typing import Optional


def parse_timedelta(delta: str) -> timedelta:
    match = re.match(r"^(\d+)([m|h])$", delta)
    if not match:
        raise ValueError("Unknown format")

    number = int(match.group(1))
    unit = match.group(2)

    if unit == "m":
        return timedelta(minutes=number)
    elif unit == "h":
        return timedelta(hours=number)

    raise ValueError("Unknown unit")
