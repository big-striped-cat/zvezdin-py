from datetime import timedelta
from decimal import Decimal

import pytz

from kline import read_klines_from_csv, get_moving_window_iterator
from logger import Logger
from strategy import strategy_basic, is_duplicate_order, maybe_close_order, log_order_opened, log_order_closed, Trend, \
    OrderType


def backtest_strategy(global_trend: Trend, klines_csv_path: str):
    klines = read_klines_from_csv(
        klines_csv_path,
        skip_header=True,
        timeframe=timedelta(minutes=5)
    )
    kline_window_size = 50

    strategy = strategy_basic
    orders = []
    orders_closed = []
    logger = Logger(tz=pytz.timezone('Europe/Moscow'))
    last_order = None
    levels_intersection_threshold = Decimal('0.5')
    order_count = 0

    for kline_window in get_moving_window_iterator(klines, kline_window_size):
        kline = kline_window[-1]

        for i, order in enumerate(orders):
            maybe_close_order(kline, order)
            if order.is_closed:
                log_order_closed(logger, kline, order)
                orders_closed.append(order)
        if any(d.is_closed for d in orders):
            orders = [d for d in orders if not d.is_closed]

        order = strategy(kline_window, logger)
        if not order:
            continue

        if global_trend == Trend.DOWN and order.order_type == OrderType.LONG:
            continue
        if global_trend == Trend.UP and order.order_type == OrderType.SHORT:
            continue

        if not last_order or not is_duplicate_order(order, last_order, levels_intersection_threshold):
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
    path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    global_trend = Trend.DOWN
    backtest_strategy(global_trend, path)
