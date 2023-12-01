import logging

from broker import Broker
from emergency import EmergencyDetector
from kline import get_moving_window_iterator
from localbroker import LocalBroker
from strategy.ordermanager import OrderManager
from strategy.emitter import SignalEmitter

logger = logging.getLogger(__name__)


def backtest_strategy(
        order_manager: OrderManager,
        emitter: SignalEmitter,
        broker: Broker,
        window_size: int
):
    order_list = order_manager.order_list
    local_broker = LocalBroker(order_list)

    kline = None
    kline_window = []
    detector = EmergencyDetector()

    for kline in broker.klines():
        if len(kline_window) < window_size:
            kline_window.append(kline)
            continue
        kline_window.append(kline)
        # now window consists of `window_size` historical klines and one current kline

        for order_id in local_broker.find_orders_for_auto_close(kline.open_time):
            logger.info('Order id=%s will be auto closed because of timeout', order_id)

            event = broker.close_order(order_id, kline)
            local_broker.handle_remote_event(event)

        for event in broker.events(kline):
            local_broker.handle_remote_event(event)

        if detector.detect(kline_window):
            logger.warning('Emergency detected at %s', kline.open_time)
            kline_window = []
            continue

        # pass historical klines
        order = emitter.get_order_request(kline_window[:-1])
        if not order:
            continue

        is_acceptable, order_ids_to_close = order_manager.is_order_acceptable(order)
        if is_acceptable:
            for order_id in order_ids_to_close:
                logger.info('order id=%s will be closed because another order was created', order_id)
                event = broker.close_order(order_id, kline)
                local_broker.handle_remote_event(event)

            event = broker.add_order(order)
            local_broker.add_order(event.order_id, order)

        kline_window.pop(0)

    if len(kline_window) < window_size:
        raise RuntimeError('Not enough klines')

    last_price = kline.close

    logger.info(f'total orders open: {len(order_list.orders_open)}')
    logger.info(f'total orders closed: {len(order_list.orders_closed)}')

    logger.info(f'profit/loss on closed orders: {order_list.profit()}')
    logger.info(f'profit/loss on open orders: {order_list.profit_unrealized(last_price)}')
