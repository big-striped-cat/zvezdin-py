from decimal import Decimal
from typing import List


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
