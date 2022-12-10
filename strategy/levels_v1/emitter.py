import enum
import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Union, Optional

from kline import Kline
from lib.levels import calc_levels_by_density, calc_levels_by_MA_extremums, get_highest_level, \
    get_lowest_level, calc_level_interactions, calc_location, calc_touch_ups, calc_touch_downs, Location, Level, \
    calc_levels_variation
from lib.trend import Trend, calc_trend
from order import Order, create_order, OrderType
from strategy.emitter import SignalEmitter
from strategy.utils import parse_timedelta


logger = logging.getLogger(__name__)


class CalcLevelsStrategy(enum.Enum):
    by_density = 1
    by_MA_extremums = 2


class JumpLevelEmitter(SignalEmitter):
    def __init__(
            self,
            price_open_to_level_ratio_threshold: Decimal = Decimal(),
            auto_close_in: timedelta = None,
            calc_levels_strategy: CalcLevelsStrategy = CalcLevelsStrategy.by_MA_extremums,
            stop_loss_level_percent: Union[Decimal, str] = None,
            profit_loss_ratio: Union[Decimal, str, int] = None,
            medium_window_size: int = None,
            small_window_size: int = None,
            min_levels_variation: Union[Decimal, str] = None
    ):
        if not isinstance(price_open_to_level_ratio_threshold, Decimal):
            price_open_to_level_ratio_threshold = Decimal(price_open_to_level_ratio_threshold)

        if isinstance(auto_close_in, str):
            auto_close_in = parse_timedelta(auto_close_in)

        if not isinstance(stop_loss_level_percent, Decimal):
            stop_loss_level_percent = Decimal(stop_loss_level_percent)

        if not isinstance(profit_loss_ratio, Decimal):
            profit_loss_ratio = Decimal(profit_loss_ratio)

        self.price_open_to_level_ratio_threshold = price_open_to_level_ratio_threshold
        self.auto_close_in = auto_close_in
        self.stop_loss_level_percent = stop_loss_level_percent
        self.profit_loss_ratio = profit_loss_ratio
        self.medium_window_size = medium_window_size
        self.small_window_size = small_window_size
        self.min_levels_variation = Decimal(min_levels_variation)

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

        # Finding trend requires medium-sized window.
        medium_window = klines[-self.medium_window_size:]
        medium_window_points = [k.close for k in medium_window]

        # Choose smaller window to calc level interactions.
        # We are interested in interactions in close surrounding of current kline.
        small_window = klines[-self.small_window_size:]
        small_window_points = [k.close for k in small_window]

        point = medium_window_points[-1]

        trend = calc_trend(medium_window_points)
        logger.info('%s trend %s', kline.open_time, trend)

        levels = self.calc_levels(small_window)

        if not levels:
            logger.warning('No levels found for window [%s - %s].',
                           small_window[0].open_time,
                           small_window[-1].open_time)
            return

        level_highest = get_highest_level(levels)
        level_lowest = get_lowest_level(levels)

        if calc_levels_variation(level_lowest, level_highest) < self.min_levels_variation:
            logger.warning('Levels are too close. Order signal will not be emitted.')
            return

        for level in (level_lowest, level_highest):
            interactions = calc_level_interactions(small_window_points, level)

            if trend in (Trend.UP, Trend.FLAT) and calc_location(point, level) == Location.UP \
                    and calc_touch_ups(interactions) >= 1 \
                    and not self.is_order_late(level, price) \
                    and level == level_lowest:
                return create_order_long(
                    kline, level,
                    stop_loss_level_percent=self.stop_loss_level_percent,
                    profit_loss_ratio=self.profit_loss_ratio,
                    auto_close_in=self.auto_close_in
                )

            if trend in (Trend.DOWN, Trend.FLAT) and calc_location(point, level) == Location.DOWN \
                    and calc_touch_downs(interactions) >= 1 \
                    and not self.is_order_late(level, price) \
                    and level == level_highest:
                return create_order_short(
                    kline, level,
                    stop_loss_level_percent=self.stop_loss_level_percent,
                    profit_loss_ratio=self.profit_loss_ratio,
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
