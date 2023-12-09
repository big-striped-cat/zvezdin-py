import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from broker import BrokerEvent, BrokerEventType
from order import OrderId, Order, get_trade_close_type, Trade
from orderlist import OrderList

logger = logging.getLogger(__name__)


@dataclass
class LocalOrderUpdate:
    price_stop_loss: Decimal


class LocalBroker:
    """
    LocalBroker: implements broker functions missing on remote broker
    * handles remote broker events: sets `order.trade_close`
    * implements order timeout
    * suggests stop loss update after partial take profit
    """

    def __init__(self, order_list: OrderList):
        self.order_list = order_list

    def add_order(self, event: BrokerEvent, order: Order):
        self.order_list.add_order(event.order_id, order)

    def close_order(self, order_id: OrderId, price: Decimal, closed_at: datetime):
        order = self.order_list.get(order_id)

        trade_type = get_trade_close_type(order.order_type)

        order.trade_close = Trade(
            type=trade_type,
            price=price,
            amount=order.trade_open.amount,
            created_at=closed_at,
        )

    def handle_remote_events(
        self, order_id: OrderId, events: list[BrokerEvent]
    ) -> Optional[LocalOrderUpdate]:
        stop_loss_changed = False
        order = self.order_list.get(order_id)

        for event in events:
            if event.type == BrokerEventType.order_open:
                pass

            if event.type in (
                BrokerEventType.order_close,
                BrokerEventType.order_close_by_take_profit,
                BrokerEventType.sub_order_close_by_take_profit,
                BrokerEventType.order_close_by_stop_loss,
            ):
                self.close_order(order_id, event.price, event.created_at)

            if event.type == BrokerEventType.sub_order_close_by_take_profit:
                sub_order = order.sub_orders[event.sub_order_index]
                if order.price_stop_loss is None:
                    order.price_stop_loss = sub_order.next_price_stop_loss
                    stop_loss_changed = True
                else:
                    order.price_stop_loss = max(
                        order.price_stop_loss, sub_order.next_price_stop_loss
                    )
                    stop_loss_changed = True

        if stop_loss_changed:
            return LocalOrderUpdate(price_stop_loss=order.price_stop_loss)

    def find_orders_for_auto_close(self, now: datetime) -> List[OrderId]:
        """
        Kind of timeout for orders
        """
        res = []

        for order_id, order in self.order_list.all():
            if order.is_closed:
                continue
            if not order.auto_close_in:
                continue
            delta = now - order.trade_open.created_at
            if delta >= order.auto_close_in:
                res.append(order_id)

        return res
