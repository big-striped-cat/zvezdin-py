from datetime import timedelta, datetime
from decimal import Decimal
from typing import Optional, List

from broker import BrokerEvent, BrokerEventType, Broker
from order import OrderId, Order, OrderType, get_trade_close_type, Trade
from strategy import Trend, is_duplicate_order, is_order_late
from utils import format_datetime


import logging
logger = logging.getLogger(__name__)


class OrderManager:
    levels_intersection_threshold = Decimal('0.5')
    order_intersection_timeout = timedelta(minutes=150)  # 2h 30m
    price_open_to_level_ratio_threshold = Decimal('0.008')

    def __init__(self, global_trend: Optional[Trend] = None):
        self.orders: dict[OrderId, Order] = {}
        self.last_order: Optional[Order] = None

        self.global_trend = global_trend

    def is_order_acceptable(self, order: Order):
        if self.global_trend == Trend.DOWN and order.order_type == OrderType.LONG:
            return False
        if self.global_trend == Trend.UP and order.order_type == OrderType.SHORT:
            return False

        if not self.last_order:
            return True

        if is_duplicate_order(
            order, self.last_order, self.levels_intersection_threshold, timeout=self.order_intersection_timeout
        ):
            return False

        if is_order_late(order, self.price_open_to_level_ratio_threshold):
            return False

        return True

    def add_order(self, order_id: OrderId, order: Order):
        assert self.is_order_acceptable(order)

        self.orders[order_id] = order
        self.last_order = order

        self.log_order_opened(order_id)

    def close_order(self, order_id: OrderId, price: Decimal, closed_at: datetime):
        order = self.orders[order_id]
        trade_type = get_trade_close_type(order.order_type)

        order.trade_close = Trade(
            type=trade_type,
            price=price,
            amount=order.trade_open.amount,
            created_at=closed_at
        )
        self.log_order_closed(order_id)

    def close_order_by_take_profit(self, order_id: OrderId, closed_at: datetime):
        order = self.orders[order_id]
        self.close_order(order_id, order.price_take_profit, closed_at)

    def close_order_by_stop_loss(self, order_id: OrderId, closed_at: datetime):
        order = self.orders[order_id]
        self.close_order(order_id, order.price_stop_loss, closed_at)

    def handle_broker_event(self, event: BrokerEvent):
        order_id = event.order_id

        if event.type == BrokerEventType.order_open:
            pass

        if event.type in (
            BrokerEventType.order_close,
            BrokerEventType.order_close_by_take_profit,
            BrokerEventType.order_close_by_stop_loss,
        ):
            self.close_order(order_id, event.price, event.created_at)

    def find_orders_for_auto_close(self, now: datetime) -> List[OrderId]:
        res = []

        for order_id, order in self.orders.items():
            if order.is_closed:
                continue
            if not order.auto_close_in:
                continue
            delta = now - order.trade_open.created_at
            if delta >= order.auto_close_in:
                res.append(order_id)

        return res

    @property
    def orders_open(self) -> dict[OrderId, Order]:
        return {order_id: order for order_id, order in self.orders.items() if not order.is_closed}

    @property
    def orders_closed(self) -> dict[OrderId, Order]:
        return {order_id: order for order_id, order in self.orders.items() if order.is_closed}

    def profit(self) -> Decimal:
        return sum((o.get_profit() for o in self.orders_closed.values()), Decimal())

    def profit_unrealized(self, price: Decimal) -> Decimal:
        return sum((o.get_profit_unrealized(price) for o in self.orders_open.values()), Decimal())

    def log_order_opened(self, order_id: OrderId):
        order = self.orders[order_id]
        opened_at = order.trade_open.created_at
        close_time_str = format_datetime(opened_at)
        level_str = f'Level[{order.level[0]}, {order.level[1]}]'
        logger.info(f'Order opened id={order_id} {order.order_type} {close_time_str} on {level_str} '
                    f'by price {order.trade_open.price}, '
                    f'take profit {order.price_take_profit}, '
                    f'stop loss {order.price_stop_loss}')

    def log_order_closed(self, order_id: OrderId):
        """
        :param order_id
        :param order: assume order.trade_close is not None
        """
        order = self.orders[order_id]
        closed_at = order.trade_close.created_at
        close_time_str = format_datetime(closed_at)
        logger.info(f'Order closed id={order_id} {order.order_type} {close_time_str} '
                    f'by price {order.trade_close.price}, '
                    f'with profit/loss {order.get_profit()}')
