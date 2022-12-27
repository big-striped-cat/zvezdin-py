from decimal import Decimal

from strategy.levels_v1.emitter import create_order_long, create_order_short
from test_kline import kline_factory


class TestCreateOrderLong:
    def test(self):
        kline = kline_factory(close=Decimal(11))
        level = (Decimal(10), Decimal(10))
        order = create_order_long(kline, level, stop_loss_level_percent=Decimal(10), profit_loss_ratio=2)
        assert order.price_stop_loss == Decimal(9)
        assert order.price_take_profit == Decimal(15)


class TestCreateOrderShort:
    def test(self):
        kline = kline_factory(close=Decimal(9))
        level = (Decimal(10), Decimal(10))
        order = create_order_short(kline, level, stop_loss_level_percent=Decimal(10), profit_loss_ratio=2)
        assert order.price_stop_loss == Decimal(11)
        assert order.price_take_profit == Decimal(5)
