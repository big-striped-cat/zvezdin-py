from order import Order
from orderlist import OrderList


class TradingContextGlobalBase:
    def __init__(
        self,
        order_list: OrderList = None
    ):
        self.order_list = order_list or OrderList()

    def is_order_acceptable(self, order: Order) -> bool:
        raise NotImplementedError
