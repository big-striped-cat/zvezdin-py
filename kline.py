from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterator


@dataclass
class Kline:
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(0)


def get_moving_window_iterator(values: Iterator, size) -> Iterator[list]:
    window = []
    for value in values:
        if len(window) == size:
            # create another list, do not mutate previous yielded list
            window = window[:]

        window.append(value)
        if len(window) > size:
            window.pop(0)

        if len(window) < size:
            continue

        yield window
