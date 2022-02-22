from decimal import Decimal
from typing import List

from strategy import ExtrapolatedList, calc_local_maximums, calc_trend_by_extremums, Trend, calc_trend


def test_extrapolated_list():
    x = ExtrapolatedList([5])
    assert x[-2] == 5
    assert x[-1] == 5
    assert x[0] == 5
    assert x[1] == 5
    assert x[2] == 5

    x = ExtrapolatedList([5, 6])
    assert x[-2] == 5
    assert x[-1] == 5
    assert x[0] == 5
    assert x[1] == 6
    assert x[2] == 6
    assert x[3] == 6


def test_calc_local_maximums():
    def calc_local_maximums_int(window: List[int], radius: int = 1):
        return calc_local_maximums([Decimal(x) for x in window], radius=radius)

    assert calc_local_maximums_int([1]) == [1]
    assert calc_local_maximums_int([1, 2]) == [2]
    assert calc_local_maximums_int([1, 2, 3]) == [3]
    assert calc_local_maximums_int([1, 3, 2]) == [3]
    assert calc_local_maximums_int([1, 3, 2, 4, 3]) == [3, 4]
    assert calc_local_maximums_int([1, 3, 2, 4, 5, 3]) == [3, 5]


def test_calc_trend_by_extremums():
    def calc_trend_by_extremums_int(window: List[int]):
        return calc_trend_by_extremums([Decimal(x) for x in window])

    assert calc_trend_by_extremums_int([5, 6, 7]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 6, 7, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 7, 6, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 8, 7, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 9, 7, 8]) == Trend.UP

    assert calc_trend_by_extremums_int([7, 6, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 6, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 6, 7, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 8, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 9, 5]) == Trend.DOWN

    assert calc_trend_by_extremums_int([7, 6, 5, 6]) == Trend.FLAT


def test_calc_trend():
    def calc_trend_int(window: List[int]):
        return calc_trend([Decimal(x) for x in window])

    assert calc_trend_int([5, 6, 7]) == Trend.FLAT
    assert calc_trend_int([5, 6, 7, 8]) == Trend.FLAT
    assert calc_trend_int([5, 7, 6, 8]) == Trend.UP
    assert calc_trend_int([5, 8, 7, 8]) == Trend.FLAT
    assert calc_trend_int([5, 9, 7, 8]) == Trend.DOWN

    assert calc_trend_int([7, 6, 5]) == Trend.FLAT
    assert calc_trend_int([8, 7, 6, 5]) == Trend.FLAT
    assert calc_trend_int([8, 6, 7, 5]) == Trend.DOWN
    assert calc_trend_int([8, 7, 8, 5]) == Trend.FLAT
    assert calc_trend_int([8, 7, 9, 5]) == Trend.UP

    assert calc_trend_int([7, 6, 5, 6]) == Trend.DOWN
