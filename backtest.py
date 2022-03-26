import logging
from broker import Broker
from kline import get_moving_window_iterator
from ordermanager import OrderManager
from strategy import strategy_basic, Trend, \
    calc_levels_by_MA_extremums

logger = logging.getLogger(__name__)


def backtest_strategy(
        global_trend: Trend,
        broker: Broker
):
    kline_window_size = 30

    strategy = strategy_basic
    calc_levels = calc_levels_by_MA_extremums

    order_manager = OrderManager(global_trend=global_trend)

    kline_window = []

    # window consists of `kline_window_size` historical klines and one current kline
    for kline_window in get_moving_window_iterator(broker.klines(), kline_window_size + 1):
        # current kline
        kline = kline_window[-1]

        for order_id in order_manager.find_orders_for_auto_close(kline.open_time):
            event = broker.close_order(order_id, kline)

            logger.info('Order id=%s will be auto closed', order_id)
            order_manager.handle_broker_event(event)

        for event in broker.events(kline):
            order_manager.handle_broker_event(event)

        # pass historical klines to strategy
        order = strategy(kline_window[:-1], calc_levels)
        if not order:
            continue

        if order_manager.is_order_acceptable(order):
            event = broker.add_order(order)
            order_manager.add_order(event.order_id, order)

    assert kline_window, 'Not enough klines'
    last_price = kline_window[-1].close

    logger.info(f'total orders open: {len(order_manager.orders_open)}')
    logger.info(f'total orders closed: {len(order_manager.orders_closed)}')

    logger.info(f'profit/loss on closed orders: {order_manager.profit()}')
    logger.info(f'profit/loss on open orders: {order_manager.profit_unrealized(last_price)}')
