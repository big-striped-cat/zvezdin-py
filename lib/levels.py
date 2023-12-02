from collections import defaultdict
from decimal import Decimal
from enum import Enum
from typing import List, Union, Callable, Tuple

from kline import Kline
from lib.indicators import calc_MA_list


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


def calc_local_maximums(
    window: List[Decimal], radius: int = 1
) -> tuple[list[int], list[Decimal]]:
    def compare(a, b):
        return b - a

    return calc_local_extremums(window, compare, radius=radius)


def calc_local_minimums(
    window: List[Decimal], radius: int = 1
) -> tuple[list[int], list[Decimal]]:
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

    points_by_sector_sorted = sorted(
        points_by_sector_count.items(), key=lambda t: t[1], reverse=True
    )
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


def group_close_points(points: List[Decimal], eps: Decimal) -> List[List[int]]:
    points_indexed = enumerate(points)

    def sort_key(t: Tuple[int, Decimal]):
        index, point = t
        return point

    points_indexed = sorted(points_indexed, key=sort_key)
    res = []
    current_level = []

    for index, point in points_indexed:
        if not current_level:
            current_level.append(index)
            continue

        if point <= points[current_level[0]] + eps:
            current_level.append(index)
            continue

        res.append(current_level)
        current_level = [index]

    if current_level:
        res.append(current_level)

    return res


def deduplicate(x: List[Decimal]) -> List[Decimal]:
    res = []
    prev = None

    for elem in x:
        if elem != prev:
            res.append(elem)
            prev = elem
            continue

    return res


def avg(x: List[Decimal]) -> Decimal:
    return round(sum(x) / len(x), 0)


def calc_levels_by_MA_extremums(klines: List[Kline]) -> List[Level]:
    ma_size = 3
    window = [k.close for k in klines]
    ma_list = calc_MA_list(window, ma_size)

    # Too much precision makes no practical sense. Also numbers look less readable.
    # Required precision depends on asset.
    ma_list = [round(x, 0) for x in ma_list]

    # Adjacent points with very close values do not build a level.
    # This indicates that trading was not much active this time.
    # Treat repeating points as a single point.
    ma_list = deduplicate(ma_list)

    indices_max, maximums = calc_local_maximums(ma_list)
    indices_min, minimums = calc_local_minimums(ma_list)
    extremums = maximums + minimums

    # eps should be mean_price * coef, where coef is configurable
    eps = Decimal("10")

    groups = [g for g in group_close_points(extremums, eps) if len(g) > 1]

    levels = [avg([extremums[index] for index in g]) for g in groups]
    levels = sorted(levels)

    radius = 5  # should be configurable
    return [(p - radius, p + radius) for p in levels]


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


def calc_levels_variation(level_1: Level, level_2: Level) -> Decimal:
    mid_1 = (level_1[0] + level_1[1]) / Decimal(2)
    mid_2 = (level_2[0] + level_2[1]) / Decimal(2)
    return abs(mid_1 / mid_2 - 1)
