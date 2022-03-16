from decimal import Decimal

from broker import BrokerSimulator, BrokerEvent, BrokerEventType
from order import TradeType, OrderType
from test_kline import kline_factory
from test_strategy import trade_factory, order_factory


class TestBrokerSimulatorEvents:
    def test_long_close_by_take_profit(self):
        broker = BrokerSimulator(klines_csv_path='/tmp/klines.csv')  # path is not used
        kline = kline_factory(
            open=Decimal(40),
            close=Decimal(50),
            high=Decimal(60),
            low=Decimal(30)
        )
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(30))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(55),
            price_stop_loss=Decimal(20)
        )

        event = broker.add_order(order)
        order_id = event.order_id

        events = broker.events(kline)
        assert events == [
            BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_take_profit,
                created_at=kline.open_time
            )
        ]

    def test_long_close_by_stop_loss(self):
        broker = BrokerSimulator(klines_csv_path='/tmp/klines.csv')  # path is not used

        kline = kline_factory(
            open=Decimal(40),
            close=Decimal(50),
            high=Decimal(60),
            low=Decimal(30)
        )
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(70))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(100),
            price_stop_loss=Decimal(35)
        )

        event = broker.add_order(order)
        order_id = event.order_id

        events = broker.events(kline)
        assert events == [
            BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_stop_loss,
                created_at=kline.open_time
            )
        ]

    def test_short_close_by_take_profit(self):
        broker = BrokerSimulator(klines_csv_path='/tmp/klines.csv')  # path is not used

        kline = kline_factory(
            open=Decimal(40),
            close=Decimal(50),
            high=Decimal(60),
            low=Decimal(30)
        )
        trade_open = trade_factory(trade_type=TradeType.SELL, price=Decimal(70))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(35),
            price_stop_loss=Decimal(100)
        )

        event = broker.add_order(order)
        order_id = event.order_id

        events = broker.events(kline)
        assert events == [
            BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_take_profit,
                created_at=kline.open_time
            )
        ]

    def test_short_close_by_stop_loss(self):
        broker = BrokerSimulator(klines_csv_path='/tmp/klines.csv')  # path is not used

        kline = kline_factory(
            open=Decimal(40),
            close=Decimal(50),
            high=Decimal(60),
            low=Decimal(30)
        )
        trade_open = trade_factory(trade_type=TradeType.SELL, price=Decimal(30))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(20),
            price_stop_loss=Decimal(55)
        )

        event = broker.add_order(order)
        order_id = event.order_id

        events = broker.events(kline)
        assert events == [
            BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_stop_loss,
                created_at=kline.open_time
            )
        ]

    def test_do_nothing(self):
        broker = BrokerSimulator(klines_csv_path='/tmp/klines.csv')  # path is not used

        kline = kline_factory(
            open=Decimal(40),
            close=Decimal(50),
            high=Decimal(60),
            low=Decimal(30)
        )
        trade_open = trade_factory(trade_type=TradeType.BUY, price=Decimal(30))
        order = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open,
            price_take_profit=Decimal(65),
            price_stop_loss=Decimal(20)
        )

        event = broker.add_order(order)
        order_id = event.order_id

        events = broker.events(kline)
        assert events == [
        ]
