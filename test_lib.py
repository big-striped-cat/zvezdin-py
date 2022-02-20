from decimal import Decimal
from typing import List

from lib import ExtrapolatedList, calcLocalMaximums, calcTrendByExtremums, Trend, calcTrend


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


def testCalcLocalMaximums():
    def calcLocalMaximumsInt(window: List[int], radius: int = 1):
        return calcLocalMaximums([Decimal(x) for x in window], radius=radius)

    assert calcLocalMaximumsInt([1]) == [1]
    assert calcLocalMaximumsInt([1, 2]) == [2]
    assert calcLocalMaximumsInt([1, 2, 3]) == [3]
    assert calcLocalMaximumsInt([1, 3, 2]) == [3]
    assert calcLocalMaximumsInt([1, 3, 2, 4, 3]) == [3, 4]
    assert calcLocalMaximumsInt([1, 3, 2, 4, 5, 3]) == [3, 5]


def test_calcTrendByExtremums():
    def calcTrendByExtremumsInt(window: List[int]):
        return calcTrendByExtremums([Decimal(x) for x in window])

    assert calcTrendByExtremumsInt([5, 6, 7]) == Trend.UP
    assert calcTrendByExtremumsInt([5, 6, 7, 8]) == Trend.UP
    assert calcTrendByExtremumsInt([5, 7, 6, 8]) == Trend.UP
    assert calcTrendByExtremumsInt([5, 8, 7, 8]) == Trend.UP
    assert calcTrendByExtremumsInt([5, 9, 7, 8]) == Trend.UP

    assert calcTrendByExtremumsInt([7, 6, 5]) == Trend.DOWN
    assert calcTrendByExtremumsInt([8, 7, 6, 5]) == Trend.DOWN
    assert calcTrendByExtremumsInt([8, 6, 7, 5]) == Trend.DOWN
    assert calcTrendByExtremumsInt([8, 7, 8, 5]) == Trend.DOWN
    assert calcTrendByExtremumsInt([8, 7, 9, 5]) == Trend.DOWN

    assert calcTrendByExtremumsInt([7, 6, 5, 6]) == Trend.FLAT


def test_calc_trend():
    def calcTrendInt(window: List[int]):
        return calcTrend([Decimal(x) for x in window])

    assert calcTrendInt([5, 6, 7]) == Trend.FLAT
    assert calcTrendInt([5, 6, 7, 8]) == Trend.FLAT
    assert calcTrendInt([5, 7, 6, 8]) == Trend.UP
    assert calcTrendInt([5, 8, 7, 8]) == Trend.UP
    assert calcTrendInt([5, 9, 7, 8]) == Trend.UP

    assert calcTrendInt([7, 6, 5]) == Trend.DOWN
    assert calcTrendInt([8, 7, 6, 5]) == Trend.DOWN
    assert calcTrendInt([8, 6, 7, 5]) == Trend.DOWN
    assert calcTrendInt([8, 7, 8, 5]) == Trend.DOWN
    assert calcTrendInt([8, 7, 9, 5]) == Trend.DOWN

    assert calcTrendInt([7, 6, 5, 6]) == Trend.FLAT
