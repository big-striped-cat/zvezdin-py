from datetime import datetime, timedelta
from decimal import Decimal

from factories import trade_factory, order_factory
from order import TradeType, OrderType
from strategy.levels_v1.ordermanager import is_duplicate_order


class TestIsDuplicateOrder:
    def test_identical_orders(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        order_a = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_a, level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        order_b = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_b, level=level_b
        )

        threshold = Decimal("0.8")
        assert is_duplicate_order(order_a, order_b, threshold)

    def test_order_different_type(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        order_a = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_a, level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        order_b = order_factory(
            order_type=OrderType.SHORT, trade_open=trade_open_b, level=level_b
        )

        threshold = Decimal("0.8")
        assert not is_duplicate_order(order_a, order_b, threshold)

    def test_orders_similar_level(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(10))
        order_a = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_a, level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(2), Decimal(11))
        order_b = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_b, level=level_b
        )

        threshold = Decimal("0.8")
        assert is_duplicate_order(order_a, order_b, threshold)

    def test_orders_different_level(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(3))
        order_a = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_a, level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(2), Decimal(4))
        order_b = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_b, level=level_b
        )

        threshold = Decimal("0.8")
        assert not is_duplicate_order(order_a, order_b, threshold)

    def test_timeout(self):
        # Levels are different, but creation time is very close
        trade_open_a = trade_factory(
            trade_type=TradeType.BUY, price=Decimal(2), created_at=datetime(2022, 2, 1)
        )
        level_a = (Decimal(1), Decimal(3))
        order_a = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_a, level=level_a
        )

        trade_open_b = trade_factory(
            trade_type=TradeType.BUY,
            price=Decimal(2),
            created_at=datetime(2022, 2, 1, 0, 5),
        )
        level_b = (Decimal(2), Decimal(4))
        order_b = order_factory(
            order_type=OrderType.LONG, trade_open=trade_open_b, level=level_b
        )

        threshold = Decimal("0.8")

        assert not is_duplicate_order(
            order_a, order_b, threshold, timeout=timedelta(minutes=2)
        )
        assert is_duplicate_order(
            order_a, order_b, threshold, timeout=timedelta(minutes=8)
        )
