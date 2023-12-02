from datetime import timedelta, date
from decimal import Decimal

import pytz

from broker import KlineDataRange, read_klines_from_csv
from kline import Kline, get_moving_window_iterator
from test_utils import datetime_from_str


def test_read_klines_from_csv_basic():
    klines = read_klines_from_csv(
        "test_data/test_kline_data.csv", timeframe=timedelta(minutes=5)
    )
    assert klines == [
        Kline(
            open_time=datetime_from_str("2022-01-20 00:00"),
            close_time=datetime_from_str("2022-01-20 00:05"),
            open=Decimal("4.4"),
            high=Decimal("4.6"),
            low=Decimal("3.9"),
            close=Decimal("4.5"),
            volume=Decimal("110.6"),
        ),
        Kline(
            open_time=datetime_from_str("2022-01-20 00:05"),
            close_time=datetime_from_str("2022-01-20 00:10"),
            open=Decimal("4.5"),
            high=Decimal("4.8"),
            low=Decimal("4.1"),
            close=Decimal("4.3"),
            volume=Decimal("48.5"),
        ),
    ]


def test_read_klines_from_csv_skip_header():
    tz = pytz.UTC
    klines = read_klines_from_csv(
        "test_data/test_kline_data_header.csv",
        skip_header=True,
        timeframe=timedelta(minutes=5),
    )
    assert klines == [
        Kline(
            open_time=datetime_from_str("2022-01-20 00:00"),
            close_time=datetime_from_str("2022-01-20 00:05"),
            open=Decimal("4.4"),
            high=Decimal("4.6"),
            low=Decimal("3.9"),
            close=Decimal("4.5"),
            volume=Decimal("110.6"),
        ),
        Kline(
            open_time=datetime_from_str("2022-01-20 00:05"),
            close_time=datetime_from_str("2022-01-20 00:10"),
            open=Decimal("4.5"),
            high=Decimal("4.8"),
            low=Decimal("4.1"),
            close=Decimal("4.3"),
            volume=Decimal("48.5"),
        ),
    ]


def test_get_moving_window_iterator():
    values = [4, 5, 6, 7]
    windows = list(get_moving_window_iterator(values, 1))
    assert windows == [[4], [5], [6], [7]]

    windows = list(get_moving_window_iterator(values, 2))
    assert windows == [[4, 5], [5, 6], [6, 7]]

    windows = list(get_moving_window_iterator(values, 3))
    assert windows == [[4, 5, 6], [5, 6, 7]]

    windows = list(get_moving_window_iterator(values, 4))
    assert windows == [[4, 5, 6, 7]]

    windows = list(get_moving_window_iterator(values, 5))
    assert windows == []


def kline_factory(
    open_time=None, close_time=None, open=None, close=None, high=None, low=None
):
    open_time = open_time or datetime_from_str("2022-01-01 18:00")
    close_time = close_time or datetime_from_str("2022-01-01 18:05")

    open = open or Decimal()
    close = close or Decimal()
    high = high or Decimal()
    low = low or Decimal()

    return Kline(
        open_time=open_time,
        close_time=close_time,
        open=open,
        close=close,
        high=high,
        low=low,
    )


class TestKlineDataRange:
    def test_path_iter_1(self):
        kdr = KlineDataRange(
            path_template="BTCBUSD-5m-%Y-%m-%d.csv",
            date_from=date(2022, 2, 18),
            date_to=date(2022, 2, 18),
        )
        assert list(kdr.path_iter()) == [
            "BTCBUSD-5m-2022-02-18.csv",
        ]

    def test_path_iter_2(self):
        kdr = KlineDataRange(
            path_template="BTCBUSD-5m-%Y-%m-%d.csv",
            date_from=date(2022, 2, 18),
            date_to=date(2022, 2, 19),
        )
        assert list(kdr.path_iter()) == [
            "BTCBUSD-5m-2022-02-18.csv",
            "BTCBUSD-5m-2022-02-19.csv",
        ]

    def test_path_iter_3(self):
        kdr = KlineDataRange(
            path_template="BTCBUSD-5m-%Y-%m-%d.csv",
            date_from=date(2022, 2, 18),
            date_to=date(2022, 2, 20),
        )
        assert list(kdr.path_iter()) == [
            "BTCBUSD-5m-2022-02-18.csv",
            "BTCBUSD-5m-2022-02-19.csv",
            "BTCBUSD-5m-2022-02-20.csv",
        ]
