from datetime import datetime
from decimal import Decimal
from typing import List, Callable

from _datetime import timedelta

from kline import Kline, read_klines_from_csv
from strategy import calc_local_maximums, calc_trend_by_extremums, Trend, calc_trend, \
    calc_levels_intersection_rate, is_duplicate_order, Order, OrderType, maybe_close_order, Trade, \
    TradeType, Level, get_highest_level, get_lowest_level, calc_levels_by_MA_extremums, calc_MA_list, \
    calc_levels_by_density, calc_local_minimums
from test_kline import kline_factory
from test_utils import datetime_from_str


def _test_calc_levels(
        calc_levels: Callable[[list[Kline]], list[Level]],
        klines_csv_path: str,
        date_from: datetime,
        date_to: datetime,
        level_low_expected: Level,
        level_high_expected: Level,
):

    klines = read_klines_from_csv(klines_csv_path, skip_header=True, timeframe=timedelta(minutes=5))

    klines_from_to = [k for k in klines if date_from <= k.open_time <= date_to]
    levels = calc_levels(klines_from_to)
    level_low = get_lowest_level(levels)
    level_high = get_highest_level(levels)

    assert level_high[0] >= level_high_expected[0]
    assert level_high[1] <= level_high_expected[1]

    assert level_low[0] >= level_low_expected[0]
    assert level_low[1] <= level_low_expected[1]


def test_calc_MA_list():
    size = 3

    window = [Decimal(3)]
    assert calc_MA_list(window, size) == [Decimal(3)]

    window = [Decimal(3), Decimal(6)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4)]

    window = [Decimal(3), Decimal(6), Decimal(9)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4), Decimal(6)]

    window = [Decimal(3), Decimal(6), Decimal(9), Decimal(9)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4), Decimal(6), Decimal(8)]


def test_calc_levels_by_MA_extremums():
    klines_csv_path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    calc_levels = calc_levels_by_MA_extremums
    # calc_levels = calc_levels_by_density

    date_from = datetime_from_str('2022-02-18 11:20')  # UTC
    date_to = datetime_from_str('2022-02-18 14:30')  # UTC
    level_low_expected = (Decimal(40160), Decimal(40330))
    level_high_expected = (Decimal(40400), Decimal(40550))

    _test_calc_levels(calc_levels, klines_csv_path, date_from, date_to, level_low_expected, level_high_expected)


def test_calc_local_maximums():
    def calc_local_maximums_int(window: List[int], radius: int = 1):
        return calc_local_maximums([Decimal(x) for x in window], radius=radius)

    assert calc_local_maximums_int([1]) == ([], [])
    assert calc_local_maximums_int([1, 2]) == ([], [])
    assert calc_local_maximums_int([1, 2, 3]) == ([], [])
    assert calc_local_maximums_int([1, 3, 2]) == ([1], [3])
    assert calc_local_maximums_int([1, 3, 2, 4, 3]) == ([1, 3], [3, 4])
    assert calc_local_maximums_int([1, 3, 2, 4, 5, 3]) == ([1, 4], [3, 5])


def test_calc_local_minimums():
    def calc_local_minimums_int(window: List[int], radius: int = 1):
        return calc_local_minimums([Decimal(x) for x in window], radius=radius)

    assert calc_local_minimums_int([9]) == ([], [])
    assert calc_local_minimums_int([9, 8]) == ([], [])
    assert calc_local_minimums_int([9, 8, 7]) == ([], [])
    assert calc_local_minimums_int([9, 7, 8]) == ([1], [7])
    assert calc_local_minimums_int([9, 7, 8, 6, 7]) == ([1, 3], [7, 6])
    assert calc_local_minimums_int([9, 7, 8, 6, 5, 7]) == ([1, 4], [7, 5])


def test_calc_trend_by_extremums():
    def calc_trend_by_extremums_int(window: List[int]):
        return calc_trend_by_extremums([Decimal(x) for x in window])

    assert calc_trend_by_extremums_int([5, 6, 7]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 6, 7, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 7, 6, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 8, 7, 8]) == Trend.UP
    assert calc_trend_by_extremums_int([5, 9, 7, 8]) == Trend.UP

    assert calc_trend_by_extremums_int([7, 6, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 6, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 6, 7, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 8, 5]) == Trend.DOWN
    assert calc_trend_by_extremums_int([8, 7, 9, 5]) == Trend.DOWN

    assert calc_trend_by_extremums_int([7, 6, 5, 6]) == Trend.FLAT


def test_calc_trend():
    def calc_trend_int(window: List[int]):
        return calc_trend([Decimal(x) for x in window])

    assert calc_trend_int([5, 7, 8, 7, 8, 7]) == Trend.FLAT
    assert calc_trend_int([5, 7, 6, 8, 7, 9]) == Trend.UP
    assert calc_trend_int([5, 8, 7, 8, 7]) == Trend.FLAT
    assert calc_trend_int([5, 9, 7, 8, 7]) == Trend.DOWN


def test_calc_levels_intersection_rate():
    level_a = (Decimal(1), Decimal(2))
    level_b = (Decimal(1), Decimal(2))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(1)

    level_a = (Decimal(1), Decimal(2))
    level_b = (Decimal(2), Decimal(3))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(0)

    level_a = (Decimal(2), Decimal(3))
    level_b = (Decimal(1), Decimal(2))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal(0)

    level_a = (Decimal(1), Decimal(3))
    level_b = (Decimal(2), Decimal(4))
    assert calc_levels_intersection_rate(level_a, level_b) == Decimal('0.5')


def trade_factory(trade_type=None, price=None, amount=None, created_at=None) -> Trade:
    trade_type = trade_type or TradeType.BUY
    price = price or Decimal()
    amount = amount or Decimal(1)
    created_at = created_at or datetime(2022, 1, 1)

    return Trade(
        type=trade_type,
        price=price,
        amount=amount,
        created_at=created_at
    )


def order_factory(order_type=None, trade_open=None, trade_close=None, level=None,
                  price_take_profit=None, price_stop_loss=None) -> Order:
    order_type = order_type or OrderType.LONG
    trade_open = trade_open or trade_factory()
    level = level or (Decimal(), Decimal())
    price_take_profit = price_take_profit or Decimal()
    price_stop_loss = price_stop_loss or Decimal()

    return Order(
        id=0,
        order_type=order_type,
        trade_open=trade_open,
        trade_close=trade_close,
        level=level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss
    )


class TestIsDuplicateOrder:
    def test_identical_orders(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        order_a = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_a,
            level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        order_b = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_b,
            level=level_b
        )

        threshold = Decimal('0.8')
        assert is_duplicate_order(order_a, order_b, threshold)

    def test_order_different_type(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(2))
        order_a = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_a,
            level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(1), Decimal(2))
        order_b = order_factory(
            order_type=OrderType.SHORT,
            trade_open=trade_open_b,
            level=level_b
        )

        threshold = Decimal('0.8')
        assert not is_duplicate_order(order_a, order_b, threshold)

    def test_orders_similar_level(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(10))
        order_a = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_a,
            level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(2), Decimal(11))
        order_b = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_b,
            level=level_b
        )

        threshold = Decimal('0.8')
        assert is_duplicate_order(order_a, order_b, threshold)

    def test_orders_different_level(self):
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_a = (Decimal(1), Decimal(3))
        order_a = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_a,
            level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2))
        level_b = (Decimal(2), Decimal(4))
        order_b = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_b,
            level=level_b
        )

        threshold = Decimal('0.8')
        assert not is_duplicate_order(order_a, order_b, threshold)

    def test_timeout(self):
        # Levels are different, but creation time is very close
        trade_open_a = trade_factory(trade_type=TradeType.BUY, price=Decimal(2), created_at=datetime(2022, 2, 1))
        level_a = (Decimal(1), Decimal(3))
        order_a = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_a,
            level=level_a
        )

        trade_open_b = trade_factory(trade_type=TradeType.BUY, price=Decimal(2), created_at=datetime(2022, 2, 1, 0, 5))
        level_b = (Decimal(2), Decimal(4))
        order_b = order_factory(
            order_type=OrderType.LONG,
            trade_open=trade_open_b,
            level=level_b
        )

        threshold = Decimal('0.8')

        assert not is_duplicate_order(order_a, order_b, threshold, timeout=timedelta(minutes=2))
        assert is_duplicate_order(order_a, order_b, threshold, timeout=timedelta(minutes=8))


class TestMaybeCloseOrder:
    def test_long_close_by_take_profit(self):
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
        assert not order.is_closed
        assert order.trade_close is None

        maybe_close_order(kline, order)

        assert order.is_closed
        assert order.trade_close.price == Decimal(55)

    def test_long_close_by_stop_loss(self):
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
        assert not order.is_closed
        assert order.trade_close is None

        maybe_close_order(kline, order)

        assert order.is_closed
        assert order.trade_close.price == Decimal(35)

    def test_short_close_by_take_profit(self):
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
        assert not order.is_closed
        assert order.trade_close is None

        maybe_close_order(kline, order)

        assert order.is_closed
        assert order.trade_close.price == Decimal(35)

    def test_short_close_by_stop_loss(self):
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
            price_take_profit=Decimal(55),
            price_stop_loss=Decimal(20)
        )
        assert not order.is_closed
        assert order.trade_close is None

        maybe_close_order(kline, order)

        assert order.is_closed
        assert order.trade_close.price == Decimal(55)

    def test_do_nothing(self):
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
        assert not order.is_closed
        assert order.trade_close is None

        maybe_close_order(kline, order)

        assert not order.is_closed
        assert order.trade_close is None
