from typing import Optional

from order import Order, OrderId
from orderlist import OrderList


class OrderManager:
    def __init__(self, order_list: Optional[OrderList] = None):
        self.order_list = order_list or OrderList()

    def is_order_acceptable(self, order: Order) -> tuple[bool, list[OrderId]]:
        """
        :return: is_acceptable, order_ids_to_close
        """
        raise NotImplementedError
