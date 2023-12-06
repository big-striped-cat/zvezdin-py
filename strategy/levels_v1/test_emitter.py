from decimal import Decimal

from order import OrderType
from strategy.levels_v1.emitter import (
    create_order,
    JumpLevelEmitter,
    split_amount,
)
from test_kline import kline_factory


class TestCreateOrder:
    def test(self):
        kline = kline_factory(close=Decimal(11))
        level = (Decimal(10), Decimal(10))
        order = create_order(
            OrderType.LONG, kline, level, amount=Decimal(1), stop_loss_level_percent=Decimal(10), profit_loss_ratio=2
        )
        assert order.price_stop_loss == Decimal(9)
        assert order.price_take_profit == Decimal(15)


class TestCreateOrderShort:
    def test(self):
        kline = kline_factory(close=Decimal(9))
        level = (Decimal(10), Decimal(10))
        order = create_order(
            OrderType.SHORT, kline, level, amount=Decimal(1), stop_loss_level_percent=Decimal(10), profit_loss_ratio=2
        )
        assert order.price_stop_loss == Decimal(11)
        assert order.price_take_profit == Decimal(5)


class TestChooseLevelsByVariation:
    def test(self):
        emitter = JumpLevelEmitter(min_levels_variation=Decimal("0.1"))
        assert emitter.choose_levels_by_variation([]) == []

        level_1 = (Decimal(10), Decimal(10))
        levels = [level_1]
        assert emitter.choose_levels_by_variation(levels) == [level_1]

        level_2 = (Decimal(11), Decimal(11))
        levels = [level_1, level_2]
        assert emitter.choose_levels_by_variation(levels) == [level_1]

        level_3 = (Decimal(12), Decimal(12))
        levels = [level_1, level_2, level_3]
        assert emitter.choose_levels_by_variation(levels) == [level_1, level_3]

        level_4 = (Decimal(13), Decimal(13))
        levels = [level_1, level_2, level_3, level_4]
        assert emitter.choose_levels_by_variation(levels) == [level_1, level_3]

        level_5 = (Decimal(14), Decimal(14))
        levels = [level_1, level_2, level_3, level_4, level_5]
        assert emitter.choose_levels_by_variation(levels) == [level_1, level_3, level_5]


def test_split_amount():
    assert split_amount(Decimal("5"), num_parts=1, precision=2) == [Decimal("5")]
    assert split_amount(Decimal("5"), num_parts=2, precision=2) == [
        Decimal("2.5"),
        Decimal("2.5"),
    ]
    assert split_amount(Decimal("5"), num_parts=3, precision=2) == [
        Decimal("1.67"),
        Decimal("1.67"),
        Decimal("1.66"),
    ]
