from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Callable, Optional

from broker import read_klines_from_csv, KlineDataRange
from kline import Kline
from lib.levels import (
    calc_local_minimums,
    calc_local_maximums,
    calc_levels_by_MA_extremums,
    get_highest_level,
    get_lowest_level,
    Level,
    group_close_points,
    deduplicate,
)
from strategy.levels_v1.ordermanager import calc_levels_intersection_rate
from test_utils import datetime_from_str


def _test_calc_levels(
    calc_levels: Callable[[list[Kline]], list[Level]],
    klines_csv_path: str,
    dt_from: datetime,
    dt_to: datetime,
    level_low_expected: Level,
    level_high_expected: Level,
):
    klines = read_klines_from_csv(
        klines_csv_path, skip_header=True, timeframe=timedelta(minutes=5)
    )

    klines_from_to = [k for k in klines if dt_from <= k.open_time <= dt_to]
    levels = calc_levels(klines_from_to)
    level_low = get_lowest_level(levels)
    level_high = get_highest_level(levels)

    assert level_high[0] >= level_high_expected[0]
    assert level_high[1] <= level_high_expected[1]

    assert level_low[0] >= level_low_expected[0]
    assert level_low[1] <= level_low_expected[1]


def test_calc_levels_by_MA_extremums_1():
    klines_csv_path = "market_data/BTCBUSD-5m-2022-02-18.csv"
    calc_levels = calc_levels_by_MA_extremums
    # calc_levels = calc_levels_by_density

    dt_from = datetime_from_str("2022-02-18 11:20")  # UTC
    dt_to = datetime_from_str("2022-02-18 14:30")  # UTC
    level_low_expected = (Decimal(40160), Decimal(40330))
    level_high_expected = (Decimal(40400), Decimal(40550))

    _test_calc_levels(
        calc_levels,
        klines_csv_path,
        dt_from,
        dt_to,
        level_low_expected,
        level_high_expected,
    )


def get_klines(kline_data_range: KlineDataRange, dt_from: datetime, dt_to: datetime):
    res = []
    for path in kline_data_range.path_iter():
        klines = read_klines_from_csv(
            path, skip_header=True, timeframe=timedelta(minutes=5)
        )
        res.extend(k for k in klines if dt_from <= k.open_time <= dt_to)
    return res


def assert_line_in_level(
    level: Level, line: Decimal, max_width: Optional[Decimal] = None
):
    assert level[0] <= line <= level[1]

    if max_width:
        assert level[1] - level[0] <= max_width


def test_group_close_points():
    assert group_close_points([], 1) == []
    assert group_close_points([100], 1) == [[0]]
    assert group_close_points([100, 101], 1) == [[0, 1]]
    assert group_close_points([100, 101, 103], 1) == [[0, 1], [2]]
    assert group_close_points([100, 101, 102], 2) == [[0, 1, 2]]
    assert group_close_points([100, 105, 106], 2) == [[0], [1, 2]]
    assert group_close_points([100, 105, 106, 110], 2) == [[0], [1, 2], [3]]

    # unsorted points
    assert group_close_points([100, 110, 106, 105], 2) == [[0], [3, 2], [1]]


def test_deduplicate():
    assert deduplicate([]) == []
    assert deduplicate([1]) == [1]
    assert deduplicate([1, 1]) == [1]
    assert deduplicate([1, 1, 2]) == [1, 2]
    assert deduplicate([1, 1, 2, 3]) == [1, 2, 3]
    assert deduplicate([1, 1, 2, 2, 3]) == [1, 2, 3]
    assert deduplicate([1, 1, 2, 2, 2, 3, 3]) == [1, 2, 3]


def test_calc_levels_by_MA_extremums_2():
    calc_levels = calc_levels_by_MA_extremums

    dt_from = datetime_from_str("2022-10-31 22:05")  # UTC
    dt_to = datetime_from_str("2022-11-01 01:10")  # UTC

    kline_data_range = KlineDataRange(
        "market_data/BTCBUSD-5m-%Y-%m-%d.csv", dt_from.date(), dt_to.date()
    )

    levels = calc_levels(get_klines(kline_data_range, dt_from, dt_to))
    assert len(levels) == 2
    assert_line_in_level(levels[0], Decimal(20447), max_width=20)
    assert_line_in_level(levels[1], Decimal(20469), max_width=20)


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
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal("0.5")
