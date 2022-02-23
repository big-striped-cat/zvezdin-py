from datetime import datetime
from decimal import Decimal
from typing import List

from strategy import ExtrapolatedList, calc_local_maximums, calc_trend_by_extremums, Trend, calc_trend, \
    calc_levels_intersection_rate, is_duplicate_decision, Decision, Order, OrderType


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


class TestIsDuplicateDecision:
    def test_identical_decisions(self):
        created_at = datetime(2022, 1, 1)

        order_a = Order(type=OrderType.LONG, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        decision_a = Decision(order=order_a, created_at=created_at, level=level_a)

        order_b = Order(type=OrderType.LONG, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        decision_b = Decision(order=order_b, created_at=created_at, level=level_b)

        threshold = Decimal('0.8')
        assert is_duplicate_decision(decision_a, decision_b, threshold)

    def test_decision_different_type(self):
        created_at = datetime(2022, 1, 1)

        order_a = Order(type=OrderType.LONG, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        decision_a = Decision(order=order_a, created_at=created_at, level=level_a)

        order_b = Order(type=OrderType.SHORT, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        decision_b = Decision(order=order_b, created_at=created_at, level=level_b)

        threshold = Decimal('0.8')
        assert not is_duplicate_decision(decision_a, decision_b, threshold)

    def test_decisions_similar_level(self):
        created_at = datetime(2022, 1, 1)

        order_a = Order(type=OrderType.LONG, price=Decimal(2))
        level_a = (Decimal(1), Decimal(10))
        decision_a = Decision(order=order_a, created_at=created_at, level=level_a)

        order_b = Order(type=OrderType.LONG, price=Decimal(2))
        level_b = (Decimal(2), Decimal(11))
        decision_b = Decision(order=order_b, created_at=created_at, level=level_b)

        threshold = Decimal('0.8')
        assert is_duplicate_decision(decision_a, decision_b, threshold)

    def test_decisions_different_level(self):
        created_at = datetime(2022, 1, 1)

        order_a = Order(type=OrderType.LONG, price=Decimal(2))
        level_a = (Decimal(1), Decimal(3))
        decision_a = Decision(order=order_a, created_at=created_at, level=level_a)

        order_b = Order(type=OrderType.LONG, price=Decimal(2))
        level_b = (Decimal(2), Decimal(4))
        decision_b = Decision(order=order_b, created_at=created_at, level=level_b)

        threshold = Decimal('0.8')
        assert not is_duplicate_decision(decision_a, decision_b, threshold)
