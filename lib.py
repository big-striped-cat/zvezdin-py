from collections import defaultdict
from decimal import Decimal
from enum import Enum
from typing import List, Tuple


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


def count_level_touch(window: List[Decimal], level: Level):
    locations = [calc_location(point, level) for point in window]
    entries = []
    exits = []
    for prev_location, next_location in zip(locations[:-1], locations[1:]):
        if prev_location == next_location:
            continue

        # todo: location ordering
        if prev_location == Location.DOWN and next_location == Location.INSIDE:
            entries.append(LevelEntry.DOWN_UP)
        if prev_location == Location.UP and next_location == Location.INSIDE:
            entries.append(LevelEntry.UP_DOWN)

        if prev_location == Location.INSIDE and next_location == Location.DOWN:
            exits.append(LevelExit.UP_DOWN)
        if prev_location == Location.INSIDE and next_location == Location.UP:
            exits.append(LevelExit.DOWN_UP)

        if prev_location == Location.DOWN and next_location == Location.UP:
            entries.append(LevelEntry.DOWN_UP)
            exits.append(LevelExit.DOWN_UP)
        if prev_location == Location.UP and next_location == Location.DOWN:
            entries.append(LevelEntry.UP_DOWN)
            exits.append(LevelExit.UP_DOWN)

