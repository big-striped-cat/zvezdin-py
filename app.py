from datetime import timedelta
from decimal import Decimal

import pytz

from kline import read_klines_from_csv, get_moving_window_iterator
from logger import Logger
from strategy import strategy_basic, is_duplicate_decision, maybe_close_order


def backtest_strategy(klines_csv_path):
    klines = read_klines_from_csv(
        klines_csv_path,
        skip_header=True,
        timeframe=timedelta(minutes=5)
    )
    kline_window_size = 50

    strategy = strategy_basic
    decisions = []
    orders_closed = []
    logger = Logger(tz=pytz.timezone('Europe/Moscow'))
    last_decision = None
    levels_intersection_threshold = Decimal('0.5')

    for kline_window in get_moving_window_iterator(klines, kline_window_size):
        kline = kline_window[-1]

        for i, decision in enumerate(decisions):
            maybe_close_order(kline, decision)
            if decision.is_closed:
                orders_closed.append(decision)
        if any(d.is_closed for d in decisions):
            decisions = [d for d in decisions if not d.is_closed]

        decision = strategy(kline_window, logger)
        if not decision:
            continue

        if not last_decision or not is_duplicate_decision(decision, last_decision, levels_intersection_threshold):
            decisions.append(decision)
            last_decision = decision
        else:
            logger.log('Duplicate decision. Skip.')

    logger.log(f'total orders: {len(decisions)}')


if __name__ == '__main__':
    path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    backtest_strategy(path)
