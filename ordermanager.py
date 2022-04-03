import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

from broker import BrokerEvent, BrokerEventType
from order import OrderId, Order, get_trade_close_type, Trade
from utils import format_datetime

logger = logging.getLogger(__name__)


class OrderManager:
    """
    OrderManager
    * is mirroring orders created on broker side
    * calculates overall profit/loss
    * implements order auto close after given period of time

    OrderManager SHOULD NOT make decisions about orders opening/closing.
    OrderManager SHOULD NOT mutate order params.
    """
    def __init__(self):
        self.orders: dict[OrderId, Order] = {}
        self.last_order: Optional[Order] = None

    def add_order(self, order_id: OrderId, order: Order):
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
