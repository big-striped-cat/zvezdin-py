from datetime import datetime
from decimal import Decimal

from kline import read_klines_from_csv, Kline


def test_read_klines_from_csv_basic():
    klines = read_klines_from_csv('test_data/test_kline_data.csv')
    assert klines == [
        Kline(
            open_time=datetime(2022, 1, 20, 3, 0),
            open=Decimal('4.4'),
            high=Decimal('4.6'),
            low=Decimal('3.9'),
            close=Decimal('4.5'),
            volume=Decimal('110.6')
        ),
        Kline(
            open_time=datetime(2022, 1, 20, 3, 5),
            open=Decimal('4.5'),
            high=Decimal('4.8'),
            low=Decimal('4.1'),
            close=Decimal('4.3'),
            volume=Decimal('48.5')
        ),
    ]


def test_read_klines_from_csv_skip_header():
    klines = read_klines_from_csv('test_data/test_kline_data_header.csv', skip_header=True)
    assert klines == [
        Kline(
            open_time=datetime(2022, 1, 20, 3, 0),
            open=Decimal('4.4'),
            high=Decimal('4.6'),
            low=Decimal('3.9'),
            close=Decimal('4.5'),
            volume=Decimal('110.6')
        ),
        Kline(
            open_time=datetime(2022, 1, 20, 3, 5),
            open=Decimal('4.5'),
            high=Decimal('4.8'),
            low=Decimal('4.1'),
            close=Decimal('4.3'),
            volume=Decimal('48.5')
        ),
    ]
