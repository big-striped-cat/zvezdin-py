from typing import List, Optional

from kline import Kline
from order import Order, create_order, OrderType
from strategy.emitter import SignalEmitter


class ConstantEmitter(SignalEmitter):
    def __init__(self):
        pass

    def get_order_request(self, klines: List[Kline]) -> Optional[Order]:
        """
        :param klines: historical klines. Current kline open price equals to klines[-1].close
        :return:
        """
        kline = klines[-1]
        level = (kline.close, kline.close)

        return create_order(
            OrderType.SHORT, kline, level
        )
