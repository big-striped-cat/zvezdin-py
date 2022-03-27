from decimal import Decimal
from datetime import timedelta
from typing import Optional

from order import Order, OrderType
from ordermanager import OrderManager
from strategy import Trend, is_duplicate_order, is_order_late


class TradingContextGlobal:
    def __init__(
        self,
        order_manager: OrderManager,
        trend: Optional[Trend] = None,
        levels_intersection_threshold: Decimal = Decimal(),
        order_intersection_timeout: timedelta = timedelta(),
        price_open_to_level_ratio_threshold: Decimal = Decimal()
    ):
        self.order_manager = order_manager

        self.trend = trend or Trend.FLAT

        self.levels_intersection_threshold = levels_intersection_threshold
        self.order_intersection_timeout = order_intersection_timeout
        self.price_open_to_level_ratio_threshold = price_open_to_level_ratio_threshold

    def is_order_acceptable(self, order: Order):
        if self.trend == Trend.DOWN and order.order_type == OrderType.LONG:
            return False
        if self.trend == Trend.UP and order.order_type == OrderType.SHORT:
            return False

        if not self.order_manager.last_order:
            return True

        if is_duplicate_order(
            order,
            self.order_manager.last_order,
            self.levels_intersection_threshold,
            timeout=self.order_intersection_timeout
        ):
            return False

        if is_order_late(order, self.price_open_to_level_ratio_threshold):
            return False

        return True
