from datetime import timedelta
from decimal import Decimal

import pytz

from kline import read_klines_from_csv, get_moving_window_iterator
from logger import Logger
from strategy import strategy_basic, is_duplicate_order, maybe_close_order


def backtest_strategy(klines_csv_path):
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

    for kline_window in get_moving_window_iterator(klines, kline_window_size):
        kline = kline_window[-1]

        for i, order in enumerate(orders):
            maybe_close_order(kline, order)
            if order.is_closed:
                orders_closed.append(order)
        if any(d.is_closed for d in orders):
            orders = [d for d in orders if not d.is_closed]

        order = strategy(kline_window, logger)
        if not order:
            continue

        if not last_order or not is_duplicate_order(order, last_order, levels_intersection_threshold):
            orders.append(order)
            last_order = order
        else:
            logger.log('Duplicate order. Skip.')

    logger.log(f'total orders: {len(orders)}')


if __name__ == '__main__':
    path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    backtest_strategy(path)
