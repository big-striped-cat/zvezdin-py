from kline import read_klines_from_csv, get_moving_window_iterator
from lib import strategy_basic


def app():
    path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    klines = read_klines_from_csv(path)
    kline_window_size = 50

    strategy = strategy_basic
    orders = []

    for kline_window in get_moving_window_iterator(klines, kline_window_size):

        if order := strategy(kline_window):
            orders.append(order)

    print(f'total orders: {len(orders)}')
