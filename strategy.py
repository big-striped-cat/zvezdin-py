import enum
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import List, Tuple, Union, Optional

from kline import Kline
from logger import Logger


class ExtrapolatedList:
    def __init__(self, values: List):
        self._values = values

    def __len__(self):
        return len(self._values)

    def __getitem__(self, item):
        if item >= len(self._values):
            return self._values[-1]
        if item <= 0:
            return self._values[0]
        return self._values[item]


class Trend(Enum):
    UP = 1
    DOWN = 2
    FLAT = 3


def calcTrend(window: List[Decimal]) -> Trend:
    """
    `calcTrend` is supposed to run on relatively large window, where some waves are present.
    """
    maximums = calcLocalMaximums(window)
    return calcTrendByExtremums(maximums)


def calcTrendByExtremums(extremums: List[Decimal]) -> Trend:
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


def calcLocalMaximums(window: List[Decimal], radius: int = 1) -> List[Decimal]:
    # todo: skip endpoints ?
    window = ExtrapolatedList(window)
    res = []
    for i in range(len(window)):
        is_extremum = True
        for j in range(i - radius, i + radius + 1):
            if window[j] > window[i]:
                is_extremum = False
                break
        if is_extremum:
            res.append(window[i])
    return res


Level = Tuple[Decimal, Decimal]


def calcLevels(window: List[Decimal]) -> List[Level]:
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


class OrderType(enum.Enum):
    LONG = 1
    SHORT = 2


@dataclass
class Order:
    type: OrderType
    kline: Kline


def create_long_order(kline: Kline, logger: Logger):
    close_time_str = logger.format_datetime(kline.close_time)
    logger.log(f'open long position {close_time_str}')

    return Order(type=OrderType.LONG, kline=kline)


def create_short_order(kline: Kline, logger: Logger):
    close_time_str = logger.format_datetime(kline.close_time)
    logger.log(f'open short position {close_time_str}')

    return Order(type=OrderType.SHORT, kline=kline)


def strategy_basic(klines: List[Kline], logger: Logger) -> Optional[Order]:
    kline = klines[-1]
    window = [k.close for k in klines]
    point = window[-1]
    trend = calcTrend(window)
    levels = calcLevels(window)
    level_highest = get_highest_level(levels)
    level_lowest = get_lowest_level(levels)

    interactions_highest = calc_level_interactions(window, level_highest)
    interactions_lowest = calc_level_interactions(window, level_lowest)

    if trend in (Trend.UP, Trend.FLAT) and calc_location(point, level_highest) == Location.UP \
            and calc_touch_ups(interactions_highest) >= 1:
        return create_long_order(kline, logger)

    if trend in (Trend.DOWN, Trend.FLAT) and calc_location(point, level_lowest) == Location.DOWN \
            and calc_touch_downs(interactions_lowest) >= 1:
        return create_short_order(kline, logger)
