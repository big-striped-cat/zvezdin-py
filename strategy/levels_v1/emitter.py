import enum
import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Union, Optional, Tuple

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
            levels_window_size_min: int = None,
            levels_window_size_max: int = None,
            min_levels_variation: Union[Decimal, str] = None,
            calc_trend_on: bool = True,
            logging_settings: Optional[dict] = None
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
        self.levels_window_size_min = levels_window_size_min
        self.levels_window_size_max = levels_window_size_max
        self.min_levels_variation = Decimal(min_levels_variation)
        self.calc_trend_on = calc_trend_on

        # Callable[[list[Kline]], list[Level]]
        self.calc_levels = {
            CalcLevelsStrategy.by_density: calc_levels_by_density,
            CalcLevelsStrategy.by_MA_extremums: calc_levels_by_MA_extremums,
        }[calc_levels_strategy]

        self.logging_settings = logging_settings or {}

    def get_order_request(self, klines: List[Kline]) -> Optional[Order]:
        """
        :param klines: historical klines. Current kline open price equals to klines[-1].close
        :return:
        """
        kline = klines[-1]

        # close price of previous kline is current price
        price = kline.close

        medium_window = klines[-self.medium_window_size:]
        medium_window_points = [k.close for k in medium_window]

        small_window = klines[-self.small_window_size:]
        small_window_points = [k.close for k in small_window]

        point = medium_window_points[-1]

        if self.calc_trend_on:
            trend = calc_trend(medium_window_points)
        else:
            trend = Trend.FLAT

        if self.logging_settings.get('trend'):
            logger.info('%s trend %s', kline.open_time, trend)

        window_size = self.find_optimal_window_size(
            klines,
            self.levels_window_size_min,
            self.levels_window_size_max
        )

        if not window_size:
            logger.warning('Optimal window not found')
            return

        window = klines[-window_size:]
        levels = self.calc_levels(window)

        level_highest = get_highest_level(levels)
        level_lowest = get_lowest_level(levels)

        for level in (level_lowest, level_highest):
            # It's important that the price interacted with level right before the trading moment
            # It means the level is relevant
            # That's why I take small window to calc interactions
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

    def find_optimal_window_size(self, klines: List[Kline], start_size: int, max_size: int) -> Optional[int]:
        """
        I need at least 2 levels which differ significally. This allows to find trade moment and trade direction.

        Problem: if the window I take is too small, then no levels will be detected. Or just 1 level will be detected.
        Or some very close levels will be detected.
        On the other side if the window is too large then irrelevant levels appear.

        Function `find_optimal_window_size` looks for minimal interval which gives at least 2 essentially different levels.

        :param klines: required `len(klines) >= max_size`
        :param start_size:
        :param max_size:
        :return: optimal window size
        """
        if len(klines) < max_size:
            logger.warning('Klines list is too small for finding optimal window')

        size = 0
        iteration = 0
        message = ''
        window = []

        while size <= max_size:
            iteration += 1
            size = start_size * iteration

            window = klines[-size:]
            levels = self.calc_levels(window)

            ok, message = self.contains_2_levels(levels)
            if ok:
                return size

        if message and window:
            logger.warning(
                '%s for window [%s - %s]',
                message,
                window[0].open_time,
                window[-1].open_time
            )

        return None

    def contains_2_levels(self, levels: List[Level]) -> Tuple[bool, str]:
        """
        Checks that `levels` contains at least 2 essentially different levels.
        """
        if not levels:
            return False, 'No levels'

        level_highest = get_highest_level(levels)
        level_lowest = get_lowest_level(levels)

        if calc_levels_variation(level_lowest, level_highest) < self.min_levels_variation:
            return False, 'Levels are too close'

        return True, ''

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
