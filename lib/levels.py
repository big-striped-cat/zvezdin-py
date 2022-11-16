from collections import defaultdict
from decimal import Decimal
from enum import Enum
from typing import List, Union, Callable, Tuple

from kline import Kline
from lib.indicators import calc_MA_list
from lib.trend import Trend


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


Level = Tuple[Decimal, Decimal]


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
