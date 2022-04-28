import enum
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Union, Optional, Callable

from kline import Kline
from level import Level
from order import Order, create_order, OrderType
from trend import Trend


def calc_trend(window: List[Decimal]) -> Trend:
    """
    `calc_trend` is supposed to run on relatively large window, where some waves are present.
    """
    _, maximums = calc_local_maximums(window)
    if len(maximums) < 2:
        raise Exception('Lack of extremums. Probably window is too small.')

    return calc_trend_by_extremums(maximums)


def calc_trend_by_extremums(extremums: List[Decimal]) -> Trend:
    high = max(extremums)
    low = min(extremums)

    if high == low:
        return Trend.FLAT

    open = extremums[0]
    close = extremums[-1]

    value = (close - open) / (high - low)
    threshold = 0.5

    if value > threshold:
        return Trend.UP
    if value < -threshold:
        return Trend.DOWN

    return Trend.FLAT


def calc_local_extremums(
        window: List[Decimal], compare: Callable[[Decimal, Decimal], int], radius: int = 1
) -> tuple[list[int], list[Decimal]]:
    indices = []
    # Exclude endpoints, because they can result in wrong extremums
    for i in range(radius, len(window) - radius):
        is_extremum = True
        for j in range(i - radius, i + radius + 1):
            if compare(window[j], window[i]) < 0:
                is_extremum = False
                break
        if is_extremum:
            indices.append(i)

    extremums = [window[i] for i in indices]
    return indices, extremums


def calc_local_maximums(window: List[Decimal], radius: int = 1) -> tuple[list[int], list[Decimal]]:
    def compare(a, b):
        return b - a

    return calc_local_extremums(window, compare, radius=radius)


def calc_local_minimums(window: List[Decimal], radius: int = 1) -> tuple[list[int], list[Decimal]]:
    def compare(a, b):
        return a - b

    return calc_local_extremums(window, compare, radius=radius)


def calc_levels_by_density(window: List[Decimal]) -> List[Level]:
    eps = Decimal(1)  # depends on asset
    value_max = max(window) + eps
    value_min = min(window)

    sectors_count = 20
    sector_len = (value_max - value_min) / sectors_count
    points_by_sector_count = defaultdict(lambda: 0)

    for point in window:
        sector_index = (point - value_min) // sector_len
        points_by_sector_count[sector_index] += 1

    points_by_sector_sorted = sorted(points_by_sector_count.items(), key=lambda t: t[1], reverse=True)
    levels_count = 5
    top_sectors = points_by_sector_sorted[:levels_count]

    res = []
    for index, count in top_sectors:
        level_bottom = value_min + index * sector_len
        level_top = level_bottom + sector_len

        # todo: precision
        level_bottom = round(level_bottom, 0)  # use 0 precision to get Decimal, not int
        level_top = round(level_top, 0)

        res.append((level_bottom, level_top))

    return res


def calc_MA(window: List[Decimal], size: int) -> Decimal:
    assert window

    if len(window) < size:
        num_of_missing_elements = size - len(window)
        window = [window[0]] * num_of_missing_elements + window

    res = sum((window[-1 - i] for i in range(size)), Decimal())
    res /= size
    return res


def calc_MA_list(window: list[Decimal], size: int) -> list[Decimal]:
    return [calc_MA(window[:i], size) for i in range(1, len(window) + 1)]


def calc_levels_by_MA_extremums(klines: List[Kline]) -> List[Level]:
    ma_size = 3
    radius = 20  # depends on asset, 50 for BTC
    window = [k.close for k in klines]
    ma_list = calc_MA_list(window, ma_size)

    # do not use plain max(), because endpoints should be eliminated
    # Also extremums allow detecting other levels
    indices_max, maximums = calc_local_maximums(ma_list)
    # print('klines max')
    # for i in indices_max:
    #     print(f'{klines[i].open_time} {round(ma_list[i])}')
    indices_min, minimums = calc_local_minimums(ma_list)
    ma_max = round(max(maximums), 0)  # precision depends on asset
    ma_min = round(min(minimums), 0)

    # print(f'ma_max {ma_max}')
    level_max = (ma_max - radius, ma_max + radius)
    level_min = (ma_min - radius, ma_min + radius)

    # print(f'level_min {level_min}')
    # print(f'level_max {level_max}')

    return [level_min, level_max]


def get_highest_level(levels: List[Level]) -> Level:
    return max(levels, key=lambda t: t[0])


def get_lowest_level(levels: List[Level]) -> Level:
    return min(levels, key=lambda t: t[0])


class Location(Enum):
    # locations relative to level
    UP = 1
    INSIDE = 0
    DOWN = -1


class LevelEntry(Enum):
    UP_DOWN = 1  # 1 0
    DOWN_UP = -1  # 0 1


class LevelExit(Enum):
    UP_DOWN = 1  # 1 0
    DOWN_UP = -1  # 0 1


class LevelIntersection(Enum):
    DOWN_UP = 1  # 0 1 2
    UP_DOWN = 2  # 2 1 0
    TOUCH_UP = 3  # 2 1 2
    TOUCH_DOWN = 4  # 0 1 0


def calc_location(point: Decimal, level: Level) -> Location:
    if point < level[0]:
        return Location.DOWN
    if point > level[1]:
        return Location.UP
    return Location.INSIDE


Interaction = Union[LevelEntry, LevelExit]


def calc_level_interactions(window: List[Decimal], level: Level) -> List[Interaction]:
    locations = [calc_location(point, level) for point in window]

    interactions = []
    for prev_location, next_location in zip(locations[:-1], locations[1:]):
        if prev_location == next_location:
            continue

        if prev_location == Location.DOWN and next_location == Location.INSIDE:
            interactions.append(LevelEntry.DOWN_UP)
        if prev_location == Location.UP and next_location == Location.INSIDE:
            interactions.append(LevelEntry.UP_DOWN)

        if prev_location == Location.INSIDE and next_location == Location.DOWN:
            interactions.append(LevelExit.UP_DOWN)
        if prev_location == Location.INSIDE and next_location == Location.UP:
            interactions.append(LevelExit.DOWN_UP)

        if prev_location == Location.DOWN and next_location == Location.UP:
            interactions.append(LevelEntry.DOWN_UP)
            interactions.append(LevelExit.DOWN_UP)
        if prev_location == Location.UP and next_location == Location.DOWN:
            interactions.append(LevelEntry.UP_DOWN)
            interactions.append(LevelExit.UP_DOWN)

    return interactions


def has_touch_up(interactions: List[Interaction]) -> bool:
    for item, next_item in zip(interactions[:-1], interactions[1:]):
        if item == LevelEntry.UP_DOWN and next_item == LevelExit.DOWN_UP:
            return True

    return False


def has_touch_down(interactions: List[Interaction]) -> bool:
    for item, next_item in zip(interactions[:-1], interactions[1:]):
        if item == LevelEntry.DOWN_UP and next_item == LevelExit.UP_DOWN:
            return True

    return False


def calc_touch_downs(interactions: List[Interaction]) -> int:
    res = 0
    for item, next_item in zip(interactions[:-1], interactions[1:]):
        if item == LevelEntry.DOWN_UP and next_item == LevelExit.UP_DOWN:
            res += 1
    return res


def calc_touch_ups(interactions: List[Interaction]) -> int:
    res = 0
    for item, next_item in zip(interactions[:-1], interactions[1:]):
        if item == LevelEntry.UP_DOWN and next_item == LevelExit.DOWN_UP:
            res += 1
    return res


class CalcLevelsStrategy(enum.Enum):
    by_density = 1
    by_MA_extremums = 2


class TradingContextLocal:
    def __init__(
            self,
            price_open_to_level_ratio_threshold: Decimal = Decimal(),
            auto_close_in: timedelta = None,
            calc_levels_strategy: CalcLevelsStrategy = CalcLevelsStrategy.by_MA_extremums
    ):
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
        :param calc_levels:
        :param logger:
        :return:
        """
        kline = klines[-1]
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
                    and not self.is_order_late(level, kline.open):
                return create_order_long(
                    kline, level, stop_loss_level_percent=Decimal('1'), profit_loss_ratio=2,
                    auto_close_in=self.auto_close_in
                )

            if trend in (Trend.DOWN, Trend.FLAT) and calc_location(point, level) == Location.DOWN \
                    and calc_touch_downs(interactions) >= 1 \
                    and not self.is_order_late(level, kline.open):
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
