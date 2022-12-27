from decimal import Decimal

from lib.indicators import calc_MA_list


def test_calc_MA_list():
    size = 3

    window = [Decimal(3)]
    assert calc_MA_list(window, size) == [Decimal(3)]

    window = [Decimal(3), Decimal(6)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4)]

    window = [Decimal(3), Decimal(6), Decimal(9)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4), Decimal(6)]

    window = [Decimal(3), Decimal(6), Decimal(9), Decimal(9)]
    assert calc_MA_list(window, size) == [Decimal(3), Decimal(4), Decimal(6), Decimal(8)]
