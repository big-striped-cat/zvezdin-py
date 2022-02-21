import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Iterator


@dataclass
class Kline:
    open_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(0)


def read_klines_from_csv(path, skip_header=False) -> list[Kline]:
    res = []
    field_names = ['open_time', 'open', 'high', 'low', 'close', 'volume']

    with open(path) as f:
        if skip_header:
            next(f)
        reader = csv.DictReader(f, fieldnames=field_names)
        for row in reader:
            open_time = datetime.fromtimestamp(int(row['open_time']) / 1000)
            open_price = Decimal(row['open'])  # clashes with `open` python keyword
            high = Decimal(row['high'])
            low = Decimal(row['low'])
            close = Decimal(row['close'])
            volume = Decimal(row['volume'])

            res.append(Kline(
                open_time=open_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume
            ))

    return res


def get_moving_window_iterator(values: list, size) -> Iterator[list]:
    start = 0
    while start + size <= len(values):
        yield values[start: start + size]
        start += 1
