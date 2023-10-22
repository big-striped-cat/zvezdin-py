from order import Order
from orderlist import OrderList


class OrderManager:
    def __init__(
        self,
        order_list: OrderList = None
    ):
        self.order_list = order_list or OrderList()

    def is_order_acceptable(self, order: Order) -> tuple[bool, list[int]]:
        """
        :return: is_acceptable, order_ids_to_close
        """
        raise NotImplementedError
