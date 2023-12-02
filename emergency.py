from decimal import Decimal
from typing import List

from kline import Kline


def mean(values: List[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def median(values: List[Decimal]) -> Decimal:
    return sorted(values)[len(values) // 2]


class EmergencyDetector:
    """
    Example implementation. Not canonical at all.
    """

    def __init__(self):
        self.cooldown_max = 10
        self.cooldown = 0

    def detect(self, klines: List[Kline]) -> bool:
        amplitudes = [abs(k.high - k.low) for k in klines]

        if amplitudes[-1] > 12 * median(amplitudes[-10:]):
            self.cooldown = self.cooldown_max
            return True

        if self.cooldown > 0:
            self.cooldown -= 1

        return False
