import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, date
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


def date_iter(date_from: date, date_to: date) -> Iterator[date]:
    d = date_from
    while d <= date_to:
        yield d
        d += timedelta(days=1)


@dataclass
class KlineDataRange:
    path_template: str
    date_from: date
    date_to: date

    def path_iter(self) -> Iterator[str]:
        for d in date_iter(self.date_from, self.date_to):
            yield d.strftime(self.path_template)


def get_klines_iter(
        path_iter: Iterator[str],
        skip_header: bool = False,
        timeframe: timedelta = timedelta()
) -> Iterator[Kline]:
    for path in path_iter:
        yield from read_klines_from_csv(path, skip_header=skip_header, timeframe=timeframe)
