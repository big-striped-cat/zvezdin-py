import enum
from datetime import timedelta
from decimal import Decimal
from typing import List, Union, Optional

from kline import Kline
from lib.levels import calc_levels_by_density, calc_levels_by_MA_extremums, calc_trend, get_highest_level, \
    get_lowest_level, calc_level_interactions, calc_location, calc_touch_ups, calc_touch_downs, Location, Level
from lib.trend import Trend
from order import Order, create_order, OrderType
from strategy.emitter import SignalEmitter
from strategy.utils import parse_timedelta


class CalcLevelsStrategy(enum.Enum):
    by_density = 1
    by_MA_extremums = 2


class JumpLevelEmitter(SignalEmitter):
    def __init__(
            self,
            price_open_to_level_ratio_threshold: Decimal = Decimal(),
            auto_close_in: timedelta = None,
            calc_levels_strategy: CalcLevelsStrategy = CalcLevelsStrategy.by_MA_extremums
    ):
        if not isinstance(price_open_to_level_ratio_threshold, Decimal):
            price_open_to_level_ratio_threshold = Decimal(price_open_to_level_ratio_threshold)

        if isinstance(auto_close_in, str):
            auto_close_in = parse_timedelta(auto_close_in)

        self.price_open_to_level_ratio_threshold = price_open_to_level_ratio_threshold
        self.auto_close_in = auto_close_in

        # Callable[[list[Kline]], list[Level]]
        self.calc_levels = {
            CalcLevelsStrategy.by_density: calc_levels_by_density,
            CalcLevelsStrategy.by_MA_extremums: calc_levels_by_MA_extremums,
        }[calc_levels_strategy]

    def get_order_request(self, klines: List[Kline]) -> Optional[Order]:
        """
        :param klines: historical klines. Current kline open price equals to klines[-1].close
        :return:
        """
        kline = klines[-1]

        # close price of previous kline is current price
        price = kline.close

        window = [k.close for k in klines]
        point = window[-1]
        trend = calc_trend(window)
        levels = self.calc_levels(klines)
        level_highest = get_highest_level(levels)
        level_lowest = get_lowest_level(levels)

        for level in (level_lowest, level_highest):
            interactions = calc_level_interactions(window, level)

            if trend in (Trend.UP, Trend.FLAT) and calc_location(point, level) == Location.UP \
                    and calc_touch_ups(interactions) >= 1 \
                    and not self.is_order_late(level, price):
                return create_order_long(
                    kline, level, stop_loss_level_percent=Decimal('1'), profit_loss_ratio=2,
                    auto_close_in=self.auto_close_in
                )

            if trend in (Trend.DOWN, Trend.FLAT) and calc_location(point, level) == Location.DOWN \
                    and calc_touch_downs(interactions) >= 1 \
                    and not self.is_order_late(level, price):
                return create_order_short(
                    kline, level, stop_loss_level_percent=Decimal('1'), profit_loss_ratio=2,
                    auto_close_in=self.auto_close_in
                )

    def is_order_late(self, level: Level, price: Decimal) -> bool:
        level_mid = (level[0] + level[1]) / 2
        price_open_to_level_ratio = abs(price - level_mid) / level_mid
        return price_open_to_level_ratio > self.price_open_to_level_ratio_threshold


def add_percent(d: Decimal, percent: Union[int, Decimal]) -> Decimal:
    if not isinstance(percent, Decimal):
        percent = Decimal(percent)

    res = d * (1 + Decimal('0.01') * percent)
    return Decimal(round(res))


def create_order_long(
        kline: Kline, level: Level,
        stop_loss_level_percent: Decimal,
        profit_loss_ratio: Union[int, Decimal],
        auto_close_in: timedelta = None
) -> Order:
    level_mid = (level[0] + level[1]) / 2

    price_stop_loss = add_percent(level_mid, -stop_loss_level_percent)
    price_take_profit = kline.close + profit_loss_ratio * (kline.close - price_stop_loss)

    return create_order(
        OrderType.LONG, kline, level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss,
        auto_close_in=auto_close_in
    )


def create_order_short(
        kline: Kline, level: Level,
        stop_loss_level_percent: Decimal,
        profit_loss_ratio: Union[int, Decimal],
        auto_close_in: timedelta = None
) -> Order:
    level_mid = (level[0] + level[1]) / 2

    price_stop_loss = add_percent(level_mid, stop_loss_level_percent)
    price_take_profit = kline.close + profit_loss_ratio * (kline.close - price_stop_loss)

    return create_order(
        OrderType.SHORT, kline, level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss,
        auto_close_in=auto_close_in
    )
