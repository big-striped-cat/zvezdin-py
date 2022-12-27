from decimal import Decimal
from enum import Enum
from typing import List

from lib.levels import calc_local_maximums


class Trend(Enum):
    UP = 1
    DOWN = 2
    FLAT = 3


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
