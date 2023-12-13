from datetime import timedelta
from decimal import Decimal
from typing import List, Optional

from kline import Kline
from order import Order, create_order, OrderType, SubOrder
from strategy.emitter import SignalEmitter


class ConstantEmitter(SignalEmitter):
    def __init__(self, order_type: OrderType):
        self.order_type = order_type

    def get_order_request(self, klines: List[Kline]) -> Optional[Order]:
        """
        :param klines: historical klines. Current kline open price equals to klines[-1].close
        :return:
        """
        kline = klines[-1]
        level = (kline.close, kline.close)
        amount = Decimal(1)
        price_take_profit = kline.close * Decimal(10)

        return create_order(
            self.order_type,
            kline,
            level,
            amount=amount,
            price_stop_loss=Decimal(0),
            auto_close_in=timedelta(hours=8),
            sub_orders=[
                SubOrder(
                    order_type=self.order_type,
                    amount=amount,
                    price_take_profit=price_take_profit,
                )
            ],
        )
