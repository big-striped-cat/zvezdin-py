from decimal import Decimal
from typing import Optional

from _datetime import timedelta

from order import Order, OrderType
from orderlist import OrderList
from strategy.tradingcontextglobal import TradingContextGlobalBase
from trend import Trend


class TradingContextGlobal(TradingContextGlobalBase):
    def __init__(
        self,
        order_list: OrderList,
        trend: Optional[Trend] = None,
        levels_intersection_threshold: Decimal = Decimal(),
        order_intersection_timeout: timedelta = timedelta()
    ):
        self.order_list = order_list

        self.trend = trend or Trend.FLAT

        self.levels_intersection_threshold = levels_intersection_threshold
        self.order_intersection_timeout = order_intersection_timeout

    def is_order_acceptable(self, order: Order):
        if self.trend == Trend.DOWN and order.order_type == OrderType.LONG:
            return False
        if self.trend == Trend.UP and order.order_type == OrderType.SHORT:
            return False

        if not self.order_list.last_order:
            return True

        if is_duplicate_order(
            order,
            self.order_list.last_order,
            self.levels_intersection_threshold,
            timeout=self.order_intersection_timeout
        ):
            return False

        return True


def is_duplicate_order(
        order_a: Order, order_b: Order,
        level_intersection_threshold: Decimal,
        timeout: Optional[timedelta] = None
):
    if order_a.order_type != order_b.order_type:
        return False

    if timeout:
        delta = order_a.trade_open.created_at - order_b.trade_open.created_at
        if abs(delta.total_seconds()) < timeout.total_seconds():
            return True

    levels_intersection_rate = calc_levels_intersection_rate(order_a.level, order_b.level)
    if levels_intersection_rate >= level_intersection_threshold:
        return True

    return False


def calc_levels_intersection_rate(level_a, level_b) -> Decimal:
    a_low, a_high = level_a
    b_low, b_high = level_b

    if a_low >= b_high:
        return Decimal(0)
    if b_low >= a_high:
        return Decimal(0)

    segment_1 = a_high - b_low
    segment_2 = b_high - a_low
    common_segment = min(segment_1, segment_2)

    size_a = a_high - a_low
    size_b = b_high - b_low

    return 2 * common_segment / (size_a + size_b)
