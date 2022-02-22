from datetime import timedelta

import pytz

from kline import read_klines_from_csv, get_moving_window_iterator
from logger import Logger
from strategy import strategy_basic


def app():
    path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    klines = read_klines_from_csv(
        path,
        skip_header=True,
        timeframe=timedelta(minutes=5)
    )
    kline_window_size = 50

    strategy = strategy_basic
    orders = []
    logger = Logger(tz=pytz.timezone('Europe/Moscow'))

    for kline_window in get_moving_window_iterator(klines, kline_window_size):

        if order := strategy(kline_window, logger):
            orders.append(order)

    print(f'total orders: {len(orders)}')


if __name__ == '__main__':
    app()
