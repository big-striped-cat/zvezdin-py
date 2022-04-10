from datetime import datetime, timedelta
from decimal import Decimal

from broker import BrokerEvent, BrokerEventType
from order import TradeType, OrderType, OrderId
from orderlist import OrderList
from ordermanager import OrderManager
from test_strategy import trade_factory, order_factory


def broker_event_factory(
        order_id: OrderId = None, event_type: BrokerEventType = None, created_at: datetime = None,
        price: Decimal = Decimal(0)
) -> BrokerEvent:
    order_id = order_id or 1
    event_type = event_type or BrokerEventType.order_open
    created_at = created_at or datetime(2022, 1, 1)

    return BrokerEvent(
        order_id=order_id,
        type=event_type,
        created_at=created_at,
        price=price
    )


class TestOrderManager:
    def test_long_close_by_take_profit(self):
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(30))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(55),
            price_stop_loss=Decimal(20)
        )
        om = OrderManager(OrderList())
        order_id = 1
        om.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_take_profit,
            price=Decimal(55)
        )
        om.handle_broker_event(event)

        assert order.is_closed
        assert order.trade_close.price == Decimal(55)

    def test_long_close_by_stop_loss(self):
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(70))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(100),
            price_stop_loss=Decimal(35)
        )
        om = OrderManager(OrderList())
        order_id = 1
        om.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_stop_loss,
            price=Decimal(35)
        )
        om.handle_broker_event(event)

        assert order.is_closed
        assert order.trade_close.price == Decimal(35)

    def test_short_close_by_take_profit(self):
        trade_open = trade_factory(trade_type=TradeType.SELL, price=Decimal(70))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(35),
            price_stop_loss=Decimal(100)
        )

        om = OrderManager(OrderList())
        order_id = 1
        om.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_take_profit,
            price=Decimal(35)
        )

        om.handle_broker_event(event)

        assert order.is_closed
        assert order.trade_close.price == Decimal(35)

    def test_short_close_by_stop_loss(self):
        trade_open = trade_factory(trade_type=TradeType.SELL, price=Decimal(30))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(20),
            price_stop_loss=Decimal(55)
        )

        om = OrderManager(OrderList())
        order_id = 1
        om.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_stop_loss,
            price=Decimal(55)
        )
        om.handle_broker_event(event)

        assert order.is_closed
        assert order.trade_close.price == Decimal(55)

    def test_find_orders_for_auto_close(self):
        om = OrderManager(OrderList())

        # auto_close is not enabled for an order
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(30), created_at=datetime(2022, 1, 1))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(65),
            price_stop_loss=Decimal(20)
        )
        om.add_order(1, order)

        now = datetime(2022, 2, 1)
        assert om.find_orders_for_auto_close(now) == []

        # auto_close is enabled
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(30), created_at=datetime(2022, 3, 1))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(65),
            price_stop_loss=Decimal(20),
            auto_close_in=timedelta(minutes=10)
        )
        om.add_order(1, order)

        # 1 minute before auto close time
        now = datetime(2022, 3, 1, 0, 9)
        assert om.find_orders_for_auto_close(now) == []

        # auto close time exactly
        now = datetime(2022, 3, 1, 0, 10)
        assert om.find_orders_for_auto_close(now) == [1]
