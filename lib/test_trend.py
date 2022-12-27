from decimal import Decimal
from typing import List

from lib.trend import calc_trend_by_extremums, Trend, calc_trend


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

    assert calc_trend_int([5, 7, 8, 7, 8, 7]) == Trend.FLAT
    assert calc_trend_int([5, 7, 6, 8, 7, 9]) == Trend.UP
    assert calc_trend_int([5, 8, 7, 8, 7]) == Trend.FLAT
    assert calc_trend_int([5, 9, 7, 8, 7]) == Trend.DOWN
