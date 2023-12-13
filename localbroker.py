import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from broker import BrokerEvent, BrokerEventType
from order import OrderId, Order, get_trade_close_type, Trade
from orderlist import OrderList
from utils import format_datetime

logger = logging.getLogger(__name__)


@dataclass
class LocalOrderUpdate:
    order_id: OrderId
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
        self.log_order_opened(order_id)

    def close_sub_order(self, event: BrokerEvent):
        if event.sub_order_index is None:
            raise ValueError("event.sub_order_index must be set")

        order = self.order_list.get(event.order_id)
        sub_order = order.sub_orders[event.sub_order_index]

        trade_type = get_trade_close_type(order.order_type)

        sub_order.trade_close = Trade(
            type=trade_type,
            price=event.price,
            amount=order.trade_open.amount,
            created_at=event.created_at,
        )
        self.log_order_closed(event.order_id)

    def handle_remote_events(
        self, order_id: OrderId, events: list[BrokerEvent]
    ) -> Optional[LocalOrderUpdate]:
        """
        :param order_id:
        :param events: must be ordered by time in ascending order
        For example if several take profits are achieved in single kline
        then events must be ordered the same as take profits.
        It allows to set trailing stop loss properly.
        :return:
        """
        order_update = None

        if not all([e.order_id == order_id for e in events]):
            logger.warning("All events must belong to order %s", order_id)

        for event in events:
            order_update = self.handle_remote_event(event)

        return order_update

    def handle_remote_event(self, event: BrokerEvent) -> Optional[LocalOrderUpdate]:
        order = self.order_list.get(event.order_id)

        if event.type == BrokerEventType.order_open:
            return None

        if event.type in (
            BrokerEventType.order_close,
            BrokerEventType.order_close_by_stop_loss,
        ):
            self.close_order(event.order_id, event.price, event.created_at)

        if (
            event.type == BrokerEventType.sub_order_close_by_take_profit
            and event.sub_order_index
        ):
            self.close_sub_order(event)

            sub_order = order.sub_orders[event.sub_order_index]
            if order.price_stop_loss is None:
                order.price_stop_loss = sub_order.next_price_stop_loss
            elif sub_order.next_price_stop_loss is not None:
                order.price_stop_loss = max(
                    order.price_stop_loss, sub_order.next_price_stop_loss
                )
            return LocalOrderUpdate(
                order_id=event.order_id, price_stop_loss=order.price_stop_loss
            )
        return None

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

    def log_order_opened(self, order_id: OrderId):
        order = self.order_list.get(order_id)
        opened_at = order.trade_open.created_at
        opened_at_str = format_datetime(opened_at)
        level_str = f"Level[{order.level[0]}, {order.level[1]}]"
        take_profits_str = ", ".join(str(s.price_take_profit) for s in order.sub_orders)
        logger.info(
            f"Order opened id={order_id} {order.order_type} {opened_at_str} on {level_str} "
            f"by price {order.trade_open.price}, "
            f"take profits {take_profits_str}, "
            f"stop loss {order.price_stop_loss}"
        )

    def log_order_closed(self, order_id: OrderId):
        """
        :param order_id
        :param order: assume order.trade_close is not None
        """
        order = self.order_list.get(order_id)

        if not order.trade_close:
            raise ValueError("order.trade_close must be set")

        closed_at = order.trade_close.created_at
        closed_at_str = format_datetime(closed_at)
        logger.info(
            f"Order closed id={order_id} {order.order_type} {closed_at_str} "
            f"by price {order.trade_close.price}, "
            f"with profit/loss {order.get_profit()}"
        )
