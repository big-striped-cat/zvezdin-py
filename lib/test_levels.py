from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Callable

from broker import read_klines_from_csv
from kline import Kline
from lib.levels import calc_local_minimums, calc_local_maximums, \
    calc_levels_by_MA_extremums, get_highest_level, get_lowest_level, Level
from strategy.levels_v1.ordermanager import calc_levels_intersection_rate
from test_utils import datetime_from_str


def _test_calc_levels(
        calc_levels: Callable[[list[Kline]], list[Level]],
        klines_csv_path: str,
        date_from: datetime,
        date_to: datetime,
        level_low_expected: Level,
        level_high_expected: Level,
):

    klines = read_klines_from_csv(klines_csv_path, skip_header=True, timeframe=timedelta(minutes=5))

    klines_from_to = [k for k in klines if date_from <= k.open_time <= date_to]
    levels = calc_levels(klines_from_to)
    level_low = get_lowest_level(levels)
    level_high = get_highest_level(levels)

    assert level_high[0] >= level_high_expected[0]
    assert level_high[1] <= level_high_expected[1]

    assert level_low[0] >= level_low_expected[0]
    assert level_low[1] <= level_low_expected[1]


def test_calc_levels_by_MA_extremums():
    klines_csv_path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    calc_levels = calc_levels_by_MA_extremums
    # calc_levels = calc_levels_by_density

    date_from = datetime_from_str('2022-02-18 11:20')  # UTC
    date_to = datetime_from_str('2022-02-18 14:30')  # UTC
    level_low_expected = (Decimal(40160), Decimal(40330))
    level_high_expected = (Decimal(40400), Decimal(40550))

    _test_calc_levels(calc_levels, klines_csv_path, date_from, date_to, level_low_expected, level_high_expected)


def test_calc_local_maximums():
    def calc_local_maximums_int(window: List[int], radius: int = 1):
        return calc_local_maximums([Decimal(x) for x in window], radius=radius)

    assert calc_local_maximums_int([1]) == ([], [])
    assert calc_local_maximums_int([1, 2]) == ([], [])
    assert calc_local_maximums_int([1, 2, 3]) == ([], [])
    assert calc_local_maximums_int([1, 3, 2]) == ([1], [3])
    assert calc_local_maximums_int([1, 3, 2, 4, 3]) == ([1, 3], [3, 4])
    assert calc_local_maximums_int([1, 3, 2, 4, 5, 3]) == ([1, 4], [3, 5])


def test_calc_local_minimums():
    def calc_local_minimums_int(window: List[int], radius: int = 1):
        return calc_local_minimums([Decimal(x) for x in window], radius=radius)

    assert calc_local_minimums_int([9]) == ([], [])
    assert calc_local_minimums_int([9, 8]) == ([], [])
    assert calc_local_minimums_int([9, 8, 7]) == ([], [])
    assert calc_local_minimums_int([9, 7, 8]) == ([1], [7])
    assert calc_local_minimums_int([9, 7, 8, 6, 7]) == ([1, 3], [7, 6])
    assert calc_local_minimums_int([9, 7, 8, 6, 5, 7]) == ([1, 4], [7, 5])


def test_calc_levels_intersection_rate():
    level_a = (Decimal(1), Decimal(2))
    level_b = (Decimal(1), Decimal(2))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(1)

    level_a = (Decimal(1), Decimal(2))
    level_b = (Decimal(2), Decimal(3))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(0)

    level_a = (Decimal(2), Decimal(3))
    level_b = (Decimal(1), Decimal(2))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(0)

    level_a = (Decimal(1), Decimal(3))
    level_b = (Decimal(2), Decimal(4))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal('0.5')
