from datetime import datetime
from decimal import Decimal

from broker import BrokerEvent, BrokerEventType
from order import TradeType, OrderType, OrderId
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
        order_manager = OrderManager()
        order_id = 1
        order_manager.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_take_profit,
            price=Decimal(55)
        )
        order_manager.handle_broker_event(event)

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
        order_manager = OrderManager()
        order_id = 1
        order_manager.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_stop_loss,
            price=Decimal(35)
        )
        order_manager.handle_broker_event(event)

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

        order_manager = OrderManager()
        order_id = 1
        order_manager.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_take_profit,
            price=Decimal(35)
        )

        order_manager.handle_broker_event(event)

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

        order_manager = OrderManager()
        order_id = 1
        order_manager.add_order(order_id, order)

        event = broker_event_factory(
            event_type=BrokerEventType.order_close_by_stop_loss,
            price=Decimal(55)
        )
        order_manager.handle_broker_event(event)

        assert order.is_closed
        assert order.trade_close.price == Decimal(55)
