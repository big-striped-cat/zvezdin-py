import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Iterator, Optional

import pytz


@dataclass
class Kline:
    open_time: datetime
    close_time: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal = Decimal(0)


def read_klines_from_csv(
        path: str,
        skip_header: bool = False,
        timeframe: timedelta = timedelta()
        ) -> list[Kline]:
    res = []
    field_names = ['open_time', 'open', 'high', 'low', 'close', 'volume']

    with open(path) as f:
        if skip_header:
            next(f)
        reader = csv.DictReader(f, fieldnames=field_names)
        for row in reader:
            open_time = datetime.fromtimestamp(int(row['open_time']) / 1000, tz=pytz.UTC)

            # close_time in Binance market data looks like 1642637099999, which is next kline open time minus 1ms.
            # This is not nice time for logging.
            # Better to construct close_time manually
            close_time = open_time + timeframe

            open_price = Decimal(row['open'])  # do not clash with `open` python keyword
            high = Decimal(row['high'])
            low = Decimal(row['low'])
            close = Decimal(row['close'])
            volume = Decimal(row['volume'])

            res.append(Kline(
                open_time=open_time,
                close_time=close_time,
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
