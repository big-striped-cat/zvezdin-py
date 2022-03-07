import enum
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Tuple, Union, Optional, Callable

from kline import Kline
from logger import Logger


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

    print(f'ma_max {ma_max}')
    level_max = (ma_max - radius, ma_max + radius)
    level_min = (ma_min - radius, ma_min + radius)

    # print(f'level_min {level_min}')
    print(f'level_max {level_max}')

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


class OrderType(enum.Enum):
    LONG = 1
    SHORT = 2

    def __str__(self):
        return {
            OrderType.LONG: 'long',
            OrderType.SHORT: 'short',
        }[self]


class TradeType(enum.Enum):
    BUY = 1
    SELL = 2

    def __str__(self):
        return {
            TradeType.BUY: 'buy',
            TradeType.SELL: 'sell',
        }[self]


@dataclass
class Trade:
    type: TradeType
    price: Decimal
    amount: Decimal
    created_at: datetime

    def value(self):
        return self.price * self.amount


@dataclass
class Order:
    id: int
    order_type: OrderType
    trade_open: Trade
    trade_close: Optional[Trade]
    level: Level
    price_take_profit: Decimal
    price_stop_loss: Decimal

    def get_profit(self, trade_close: Optional[Trade] = None):
        trade_close = trade_close or self.trade_close
        profit = trade_close.value() - self.trade_open.value()
        return {
            OrderType.LONG: profit,
            OrderType.SHORT: -profit,
        }[self.order_type]

    def get_profit_unrealized(self, kline: Kline):
        trade_close = Trade(
            type=get_trade_close_type(self.order_type),
            price=kline.close,
            amount=self.trade_open.amount,
            created_at=kline.close_time
        )
        return self.get_profit(trade_close=trade_close)

    def is_profit(self):
        return self.get_profit() > 0

    @property
    def is_closed(self):
        return self.trade_close is not None


def log_order_opened(logger: Logger, kline: Kline, order: Order):
    close_time_str = logger.format_datetime(kline.close_time)
    level_str = f'Level[{order.level[0]}, {order.level[1]}]'
    logger.log(f'Order opened id={order.id} {order.order_type} {close_time_str} on {level_str} '
               f'by price {order.trade_open.price}, '
               f'take profit {order.price_take_profit}, '
               f'stop loss {order.price_stop_loss}')


def log_order_closed(logger: Logger, kline: Kline, order: Order):
    close_time_str = logger.format_datetime(kline.close_time)
    logger.log(f'Order closed id={order.id} {order.order_type} {close_time_str} '
               f'by price {order.trade_close.price}, '
               f'with profit/loss {order.get_profit()}')


def get_trade_open_type(order_type: OrderType) -> TradeType:
    return {
        OrderType.LONG: TradeType.BUY,
        OrderType.SHORT: TradeType.SELL,
    }[order_type]


def get_trade_close_type(order_type: OrderType) -> TradeType:
    return {
        OrderType.LONG: TradeType.SELL,
        OrderType.SHORT: TradeType.BUY,
    }[order_type]


def create_order(
        order_type: OrderType, kline: Kline, level: Level, logger: Logger,
        price_take_profit=None, price_stop_loss=None, id=None
        ) -> Order:
    price_take_profit = price_take_profit or Decimal()
    price_stop_loss = price_stop_loss or Decimal()
    id = id or 0

    close_time_str = logger.format_datetime(kline.close_time)
    level_str = f'Level[{level[0]}, {level[1]}]'
    logger.debug(f'create order {order_type} {close_time_str} on {level_str}, '
                 f'take profit {price_take_profit}, stop loss {price_stop_loss}')

    trade_type = get_trade_open_type(order_type)

    trade_open = Trade(
        type=trade_type,
        price=kline.close,
        amount=Decimal(1),
        created_at=kline.close_time
    )

    return Order(
        id=id,
        order_type=order_type,
        trade_open=trade_open,
        trade_close=None,
        level=level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss,
    )


def add_percent(d: Decimal, percent: Union[int, Decimal]) -> Decimal:
    if not isinstance(percent, Decimal):
        percent = Decimal(percent)

    res = d * (1 + Decimal('0.01') * percent)
    return Decimal(round(res))


def create_order_long(kline: Kline, level: Level, logger: Logger) -> Order:
    price_take_profit = add_percent(kline.close, 2)
    price_stop_loss = add_percent(kline.close, -1)

    return create_order(
        OrderType.LONG, kline, level, logger,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss
    )


def create_order_short(kline: Kline, level: Level, logger: Logger) -> Order:
    price_take_profit = add_percent(kline.close, -2)
    price_stop_loss = add_percent(kline.close, 1)

    return create_order(
        OrderType.SHORT, kline, level, logger,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss
    )


def strategy_basic(
        klines: List[Kline], calc_levels: Callable[[list[Kline]], list[Level]], logger: Logger
) -> Optional[Order]:
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
    levels = calc_levels(klines)
    level_highest = get_highest_level(levels)
    level_lowest = get_lowest_level(levels)

    for level in (level_lowest, level_highest):
        interactions = calc_level_interactions(window, level)

        if trend in (Trend.UP, Trend.FLAT) and calc_location(point, level) == Location.UP \
                and calc_touch_ups(interactions) >= 1:
            return create_order_long(kline, level, logger)

        if trend in (Trend.DOWN, Trend.FLAT) and calc_location(point, level) == Location.DOWN \
                and calc_touch_downs(interactions) >= 1:
            return create_order_short(kline, level, logger)


def calc_levels_intersection_rate(level_a, level_b) -> Decimal:
    a_low, a_high = level_a
    b_low, b_high = level_b

    if a_low >= b_high:
        return Decimal(0)
    if b_low >= a_high:
        return Decimal(0)

    segment_1 = a_high - b_low
    segment_2 = b_high - a_low
    common_segment = min(segment_1, segment_2)

    size_a = a_high - a_low
    size_b = b_high - b_low

    return 2 * common_segment / (size_a + size_b)


def is_duplicate_order(
        order_a: Order, order_b: Order,
        level_intersection_threshold: Decimal,
        timeout: Optional[timedelta] = None
):
    if order_a.order_type != order_b.order_type:
        return False

    if timeout:
        delta = order_a.trade_open.created_at - order_b.trade_open.created_at
        if abs(delta.total_seconds()) < timeout.total_seconds():
            return True

    levels_intersection_rate = calc_levels_intersection_rate(order_a.level, order_b.level)
    if levels_intersection_rate >= level_intersection_threshold:
        return True

    return False


def is_order_late(order: Order, threshold: Decimal):
    level_mid = (order.level[0] + order.level[1]) / 2
    price_open_to_level_ratio = abs(order.trade_open.price - level_mid) / level_mid
    return price_open_to_level_ratio > threshold


def is_price_achieved(kline: Kline, price: Decimal) -> bool:
    return kline.low <= price <= kline.high


def is_take_profit_achieved(kline: Kline, order: Order) -> bool:
    return is_price_achieved(kline, order.price_take_profit)


def is_stop_loss_achieved(kline: Kline, order: Order) -> bool:
    return is_price_achieved(kline, order.price_stop_loss)


def close_order_by_take_profit(kline: Kline, order: Order):
    trade_type = get_trade_close_type(order.order_type)

    order.trade_close = Trade(
        type=trade_type,
        price=order.price_take_profit,
        amount=order.trade_open.amount,
        created_at=kline.open_time,  # or close_time or ... ?
    )


def close_order_by_stop_loss(kline: Kline, order: Order):
    trade_type = get_trade_close_type(order.order_type)

    order.trade_close = Trade(
        type=trade_type,
        price=order.price_stop_loss,
        amount=order.trade_open.amount,
        created_at=kline.open_time,  # or close_time or ... ?
    )


def maybe_close_order(kline: Kline, order: Order):
    if is_take_profit_achieved(kline, order) and is_stop_loss_achieved(kline, order):
        raise Exception('Undefined behaviour. Take profit and stop loss both achieved.')

    if is_take_profit_achieved(kline, order):
        close_order_by_take_profit(kline, order)

    if is_stop_loss_achieved(kline, order):
        close_order_by_stop_loss(kline, order)
