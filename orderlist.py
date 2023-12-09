import logging
from decimal import Decimal
from typing import Optional, Iterable

from order import OrderId, Order

logger = logging.getLogger(__name__)


class OrderList:
    """
    OrderList
    * is mirroring orders created on broker side
    * calculates overall profit/loss

    Think of it as wrapper around database table.

    OrderList SHOULD NOT make decisions about orders opening/closing.
    OrderList SHOULD NOT mutate order params.
    """

    orders: dict[OrderId, Order]
    last_order: Optional[Order]

    def __init__(self):
        self.orders = {}
        self.last_order = None

    def all(self) -> Iterable[tuple[OrderId, Order]]:
        return self.orders.items()

    def get(self, order_id: OrderId) -> Order:
        return self.orders[order_id]

    def add_order(self, order_id: OrderId, order: Order):
        self.orders[order_id] = order
        self.last_order = order

    @property
    def orders_open(self) -> dict[OrderId, Order]:
        return {
            order_id: order
            for order_id, order in self.orders.items()
            if not order.is_closed
        }

    @property
    def orders_closed(self) -> dict[OrderId, Order]:
        return {
            order_id: order
            for order_id, order in self.orders.items()
            if order.is_closed
        }

    def profit(self) -> Decimal:
        return sum((o.get_profit() for o in self.orders_closed.values()), Decimal())

    def profit_unrealized(self, price: Decimal) -> Decimal:
        return sum(
            (o.get_profit(price) for o in self.orders_open.values()),
            Decimal(),
        )
