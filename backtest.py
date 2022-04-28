import logging

from broker import Broker
from kline import get_moving_window_iterator
from ordermanager import OrderManager
from strategy.tradingcontextglobal import TradingContextGlobalBase
from strategy.tradingcontextlocal import TradingContextLocalBase

logger = logging.getLogger(__name__)


def backtest_strategy(
        context_global: TradingContextGlobalBase,
        context_local: TradingContextLocalBase,
        broker: Broker
):
    kline_window_size = 30

    order_list = context_global.order_list
    order_manager = OrderManager(order_list)

    kline_window = []

    # window consists of `kline_window_size` historical klines and one current kline
    for kline_window in get_moving_window_iterator(broker.klines(), kline_window_size + 1):
        # current kline
        kline = kline_window[-1]

        for order_id in order_manager.find_orders_for_auto_close(kline.open_time):
            logger.info('Order id=%s will be auto closed', order_id)

            event = broker.close_order(order_id, kline)
            order_manager.handle_broker_event(event)

        for event in broker.events(kline):
            order_manager.handle_broker_event(event)

        # pass historical klines
        order = context_local.get_order_request(kline_window[:-1])
        if not order:
            continue

        if context_global.is_order_acceptable(order):
            event = broker.add_order(order)
            order_manager.add_order(event.order_id, order)

    assert kline_window, 'Not enough klines'
    last_price = kline_window[-1].close

    logger.info(f'total orders open: {len(order_list.orders_open)}')
    logger.info(f'total orders closed: {len(order_list.orders_closed)}')

    logger.info(f'profit/loss on closed orders: {order_list.profit()}')
    logger.info(f'profit/loss on open orders: {order_list.profit_unrealized(last_price)}')
