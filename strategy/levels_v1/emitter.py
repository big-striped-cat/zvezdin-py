import enum
import logging
from datetime import timedelta
from decimal import Decimal
from typing import List, Union, Optional, Tuple

from kline import Kline
from lib.levels import (
    calc_levels_by_density,
    calc_levels_by_MA_extremums,
    get_highest_level,
    get_lowest_level,
    calc_level_interactions,
    calc_location,
    calc_touch_ups,
    calc_touch_downs,
    Location,
    Level,
    calc_levels_variation,
)
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
        auto_close_in: timedelta = timedelta(),
        calc_levels_strategy: CalcLevelsStrategy = CalcLevelsStrategy.by_MA_extremums,
        stop_loss_level_percent: Union[Decimal, str] = Decimal(0),
        profit_loss_ratio: Union[Decimal, str, int] = Decimal(1),
        trend_window_size: int = 0,
        interactions_window_size: int = 0,
        levels_window_size_min: int = 0,
        levels_window_size_max: int = 0,
        min_levels_variation: Union[Decimal, str] = 0,
        calc_trend_on: bool = True,
        min_level_interactions: int = 10,
        logging_settings: Optional[dict] = None,
        sub_orders_count: int = 1,
        create_lucky_order: bool = True,
        lucky_profit_loss_ratio: Union[Decimal, str, int] = Decimal(10),
    ):
        if not isinstance(price_open_to_level_ratio_threshold, Decimal):
            price_open_to_level_ratio_threshold = Decimal(
                price_open_to_level_ratio_threshold
            )

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
        self.trend_window_size = trend_window_size
        self.interactions_window_size = interactions_window_size
        self.levels_window_size_min = levels_window_size_min
        self.levels_window_size_max = levels_window_size_max
        self.min_levels_variation = Decimal(min_levels_variation)
        self.calc_trend_on = calc_trend_on
        self.min_level_interactions = min_level_interactions
        self.sub_orders_count = sub_orders_count
        self.create_lucky_order = create_lucky_order
        self.lucky_profit_loss_ratio = lucky_profit_loss_ratio

        self.calc_levels_strategy = calc_levels_strategy

        self.logging_settings = logging_settings or {}

    def get_order_request(self, klines: List[Kline]) -> Optional[Order]:
        """
        :param klines: historical klines. Current kline open price equals to klines[-1].close
        :return:
        """
        kline = klines[-1]

        # close price of previous kline is current price
        price = kline.close

        trend_window = klines[-self.trend_window_size :]
        trend_window_points = [k.close for k in trend_window]

        interactions_window = klines[-self.interactions_window_size :]
        interactions_window_points = [k.close for k in interactions_window]

        point = trend_window_points[-1]

        if self.calc_trend_on:
            trend = calc_trend(trend_window_points)
        else:
            trend = Trend.FLAT

        if self.logging_settings.get("trend"):
            logger.info("%s trend %s", kline.open_time, trend)

        window_size = self.find_optimal_window_size(
            klines, self.levels_window_size_min, self.levels_window_size_max
        )

        if not window_size:
            logger.warning("Optimal window not found")
            return

        window = klines[-window_size:]
        levels = self.calc_levels(window)
        levels = sorted(levels, key=lambda level: (level[0] + level[1]) / Decimal(2))

        level_highest = get_highest_level(levels)
        level_lowest = get_lowest_level(levels)

        for level in (level_lowest, level_highest):
            # It's important that the price interacted with level right before the trading moment
            # It means the level is relevant
            # That's why interactions window must be smaller than global window
            interactions = calc_level_interactions(interactions_window_points, level)

            if (
                trend in (Trend.UP, Trend.FLAT)
                and calc_location(point, level) == Location.UP
                and len(interactions) >= self.min_level_interactions
                and not self.is_order_late(level, price)
                and level == level_lowest
            ):
                close_levels = self.choose_levels_by_variation(levels)

                return create_order_long(
                    kline,
                    level,
                    stop_loss_level_percent=self.stop_loss_level_percent,
                    close_levels=close_levels,
                    lucky_profit_loss_ratio=self.lucky_profit_loss_ratio,
                    auto_close_in=self.auto_close_in,
                )

            if (
                trend in (Trend.DOWN, Trend.FLAT)
                and calc_location(point, level) == Location.DOWN
                and len(interactions) >= self.min_level_interactions
                and not self.is_order_late(level, price)
                and level == level_highest
            ):
                # highest level must be first level included to `close_levels`
                close_levels = list(reversed(levels))
                close_levels = self.choose_levels_by_variation(close_levels)

                return create_order_short(
                    kline,
                    level,
                    stop_loss_level_percent=self.stop_loss_level_percent,
                    close_levels=close_levels,
                    lucky_profit_loss_ratio=self.lucky_profit_loss_ratio,
                    auto_close_in=self.auto_close_in,
                )

    def calc_levels(self, klines: list[Kline]) -> list[Level]:
        calc_func = {
            CalcLevelsStrategy.by_density: calc_levels_by_density,
            CalcLevelsStrategy.by_MA_extremums: calc_levels_by_MA_extremums,
        }[self.calc_levels_strategy]

        levels = calc_func(klines)
        return levels

    def find_optimal_window_size(
        self, klines: List[Kline], start_size: int, max_size: int
    ) -> Optional[int]:
        """
        I need at least `num_levels` levels which differ significally. This allows to find trade moment and trade direction.

        Problem: if the window I take is too interactions, then no levels will be detected. Or just 1 level will be detected.
        Or some very close levels will be detected.
        On the other side if the window is too large then irrelevant levels appear.

        Function `find_optimal_window_size` looks for minimal interval which gives at least 2 essentially different levels.

        :param klines: required `len(klines) >= max_size`
        :param start_size:
        :param max_size:
        :return: optimal window size
        """
        if len(klines) < max_size:
            logger.warning("Klines list is too interactions for finding optimal window")

        size = 0
        iteration = 0
        message = ""
        window = []

        while size <= max_size:
            iteration += 1
            size = start_size * iteration

            window = klines[-size:]
            levels = self.calc_levels(window)
            levels = sorted(
                levels, key=lambda level: (level[0] + level[1]) / Decimal(2)
            )
            levels = self.choose_levels_by_variation(levels)

            min_levels = self.sub_orders_count + 1
            if self.create_lucky_order:
                # Lucky order does not require existing level as take-profit level
                min_levels -= 1

            if len(levels) >= min_levels:
                return size

        if message and window:
            logger.warning(
                "%s for window [%s - %s]",
                message,
                window[0].open_time,
                window[-1].open_time,
            )

        return None

    def choose_levels_by_variation(self, levels: list[Level]) -> list[Level]:
        """
        :param levels: must be sorted
        :return: Given `levels` choose levels where each 2 neighbour levels have variation
            greater than `self.min_levels_variation`.
            First level is always included.
        """

        if not levels:
            return []

        prev_level_index = 0
        prev_level = levels[0]
        res = [prev_level]

        while prev_level_index < len(levels):
            next_level_index = None
            next_level = None
            for next_level_index in range(prev_level_index + 1, len(levels)):
                if (
                    calc_levels_variation(prev_level, levels[next_level_index])
                    >= self.min_levels_variation
                ):
                    next_level = levels[next_level_index]
                    break
            if not next_level:
                break
            res.append(next_level)
            prev_level = next_level
            prev_level_index = next_level_index

        return res

    def is_order_late(self, level: Level, price: Decimal) -> bool:
        level_mid = (level[0] + level[1]) / 2
        price_open_to_level_ratio = abs(price - level_mid) / level_mid
        return price_open_to_level_ratio > self.price_open_to_level_ratio_threshold


def create_order_long(
    kline: Kline,
    level: Level,
    stop_loss_level_percent: Decimal,
    close_levels: list[Level],
    auto_close_in: timedelta = None,
    sub_orders_count: int = 1,
    create_lucky_order: bool = False,
    lucky_profit_loss_ratio: Union[int, Decimal, None] = None,
) -> Order:
    sub_orders = []

    normal_orders_count = (
        sub_orders_count - 1 if create_lucky_order else sub_orders_count
    )

    level_mid = (level[0] + level[1]) / 2
    price_stop_loss = add_percent(level_mid, -stop_loss_level_percent)

    for order_index in range(normal_orders_count):
        close_level = close_levels[order_index]
        close_level_mid = (close_level[0] + close_level[1]) / 2

        sub_orders.append(
            create_order(
                OrderType.LONG,
                kline,
                level,
                price_take_profit=close_level_mid,
                price_stop_loss=price_stop_loss,
            )
        )

    if create_lucky_order:
        price_take_profit = kline.close + lucky_profit_loss_ratio * (
            kline.close - price_stop_loss
        )
        sub_orders.append(
            create_order(
                OrderType.LONG,
                kline,
                level,
                price_take_profit=price_take_profit,
                price_stop_loss=price_stop_loss,
            )
        )

    return create_order(
        OrderType.LONG, kline, level, auto_close_in=auto_close_in, sub_orders=sub_orders
    )


def create_order_short(
    kline: Kline,
    level: Level,
    stop_loss_level_percent: Decimal,
    close_levels: list[Level],
    auto_close_in: timedelta = None,
    sub_orders_count: int = 1,
    create_lucky_order: bool = False,
    lucky_profit_loss_ratio: Union[int, Decimal, None] = None,
) -> Order:
    sub_orders = []

    normal_orders_count = (
        sub_orders_count - 1 if create_lucky_order else sub_orders_count
    )

    level_mid = (level[0] + level[1]) / 2
    price_stop_loss = add_percent(level_mid, stop_loss_level_percent)

    for order_index in range(normal_orders_count):
        close_level = close_levels[order_index]
        close_level_mid = (close_level[0] + close_level[1]) / 2

        sub_orders.append(
            create_order(
                OrderType.SHORT,
                kline,
                level,
                price_take_profit=close_level_mid,
                price_stop_loss=price_stop_loss,
            )
        )

    if create_lucky_order:
        price_take_profit = kline.close + lucky_profit_loss_ratio * (
            kline.close - price_stop_loss
        )

        sub_orders.append(
            create_order(
                OrderType.SHORT,
                kline,
                level,
                price_take_profit=price_take_profit,
                price_stop_loss=price_stop_loss,
            )
        )

    return create_order(
        OrderType.SHORT,
        kline,
        level,
        auto_close_in=auto_close_in,
        sub_orders=sub_orders,
    )


def add_percent(d: Decimal, percent: Union[int, Decimal]) -> Decimal:
    if not isinstance(percent, Decimal):
        percent = Decimal(percent)

    res = d * (1 + Decimal("0.01") * percent)
    return Decimal(round(res))


def split_amount(amount: Decimal, num_parts: int, precision: int) -> list[Decimal]:
    part = round(amount / Decimal(num_parts), precision)
    parts = [part] * num_parts
    dust = amount - sum(parts)  # may be negative
    parts[-1] += dust
    return parts
