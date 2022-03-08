from dataclasses import dataclass
from datetime import timedelta, date
from decimal import Decimal
from typing import Optional, Iterator

import pytz

from kline import read_klines_from_csv, get_moving_window_iterator, KlineDataRange, get_klines_iter
from logger import Logger
from strategy import strategy_basic, is_duplicate_order, maybe_close_order, log_order_opened, log_order_closed, Trend, \
    OrderType, calc_levels_by_density, calc_levels_by_MA_extremums, is_order_late


def backtest_strategy(
        global_trend: Trend,
        klines_csv_path: Optional[str] = None,
        kline_data_range: Optional[KlineDataRange] = None
):
    assert klines_csv_path or kline_data_range
    path_iter = (klines_csv_path, ) if klines_csv_path else kline_data_range.path_iter()

    klines = get_klines_iter(
        path_iter,
        skip_header=False,
        timeframe=timedelta(minutes=5)
    )
    kline_window_size = 30

    strategy = strategy_basic
    calc_levels = calc_levels_by_MA_extremums
    orders = []
    orders_closed = []
    logger = Logger(tz=pytz.timezone('Europe/Moscow'))
    last_order = None

    # strategy config
    levels_intersection_threshold = Decimal('0.5')
    order_intersection_timeout = timedelta(minutes=5 * kline_window_size)
    price_open_to_level_ratio_threshold = Decimal('0.008')

    order_count = 0

    # window consists of `kline_window_size` historical klines and one current kline
    for kline_window in get_moving_window_iterator(klines, kline_window_size + 1):
        # current kline
        kline = kline_window[-1]

        for i, order in enumerate(orders):
            maybe_close_order(kline, order)
            if order.is_closed:
                log_order_closed(logger, kline, order)
                orders_closed.append(order)
        if any(d.is_closed for d in orders):
            orders = [d for d in orders if not d.is_closed]

        # pass historical klines to strategy
        order = strategy(kline_window[:-1], calc_levels, logger)
        if not order:
            continue

        if global_trend == Trend.DOWN and order.order_type == OrderType.LONG:
            continue
        if global_trend == Trend.UP and order.order_type == OrderType.SHORT:
            continue

        if not last_order or (not is_duplicate_order(
                order, last_order, levels_intersection_threshold, timeout=order_intersection_timeout
        ) and not is_order_late(order, price_open_to_level_ratio_threshold)
        ):
            order_count += 1
            order.id = order_count
            log_order_opened(logger, kline, order)
            orders.append(order)
            last_order = order
        else:
            logger.debug('Duplicate order. Skip.')

    profit_unrealized = sum((o.get_profit_unrealized(kline) for o in orders), Decimal())
    profit_closed = sum((o.get_profit() for o in orders_closed), Decimal())

    logger.log(f'total orders open: {len(orders)}')
    logger.log(f'total orders closed: {len(orders_closed)}')

    logger.log(f'profit/loss on closed orders: {profit_closed}')
    logger.log(f'profit/loss on open orders: {profit_unrealized}')


if __name__ == '__main__':
    # path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    path_template = 'market_data/BTCBUSD-5m-%Y-%m-%d.csv'
    date_from = date(2022, 2, 18)
    date_to = date(2022, 2, 19)

    kline_data_range = KlineDataRange(
        path_template=path_template,
        date_from=date_from,
        date_to=date_to
    )

    global_trend = Trend.DOWN
    backtest_strategy(global_trend, kline_data_range=kline_data_range)
