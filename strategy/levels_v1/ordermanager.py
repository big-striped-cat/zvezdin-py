from decimal import Decimal
from typing import Optional, Union, cast

from datetime import timedelta

from lib.trend import Trend
from order import Order, OrderType, OrderId
from orderlist import OrderList
from strategy.ordermanager import OrderManager
from strategy.utils import parse_timedelta


class DeduplicateOrderManager(OrderManager):
    def __init__(
        self,
        order_list: OrderList,
        trend: Optional[Union[Trend, str]] = None,
        levels_intersection_threshold: Union[Decimal, str] = Decimal(),
        order_intersection_timeout: Union[timedelta, str] = timedelta(),
        allow_parallel_orders: bool = False,
    ):
        super().__init__(order_list)

        if isinstance(trend, str):
            trend = Trend[trend.upper()]

        if isinstance(levels_intersection_threshold, str):
            levels_intersection_threshold = Decimal(levels_intersection_threshold)

        if isinstance(order_intersection_timeout, str):
            order_intersection_timeout = parse_timedelta(order_intersection_timeout)

        self.trend = trend or Trend.FLAT

        self.levels_intersection_threshold = levels_intersection_threshold
        self.order_intersection_timeout = cast(timedelta, order_intersection_timeout)
        self.allow_parallel_orders = allow_parallel_orders

    def is_order_acceptable(self, order: Order) -> tuple[bool, list[OrderId]]:
        if self.trend == Trend.DOWN and order.order_type == OrderType.LONG:
            return False, []
        if self.trend == Trend.UP and order.order_type == OrderType.SHORT:
            return False, []

        if not self.order_list.orders_open:
            return True, []

        if not self.allow_parallel_orders:
            for prev_order in self.order_list.orders_open.values():
                delta = order.trade_open.created_at - prev_order.trade_open.created_at
                if delta <= self.order_intersection_timeout:
                    return False, []

            return True, list(self.order_list.orders_open.keys())

        for existing_order_id, existing_order in self.order_list.orders_open.items():
            if is_duplicate_order(
                order,
                existing_order,
                self.levels_intersection_threshold,
                timeout=self.order_intersection_timeout,
            ):
                return False, []

        return True, []


def is_duplicate_order(
    order_a: Order,
    order_b: Order,
    level_intersection_threshold: Decimal,
    timeout: Optional[timedelta] = None,
):
    if order_a.order_type != order_b.order_type:
        return False

    if timeout:
        delta = order_a.trade_open.created_at - order_b.trade_open.created_at
        if abs(delta.total_seconds()) < timeout.total_seconds():
            return True

    levels_intersection_rate = calc_levels_intersection_rate(
        order_a.level, order_b.level
    )
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
