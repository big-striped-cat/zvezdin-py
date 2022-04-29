from order import Order
from strategy.ordermanager import OrderManager


class HoldOrderManager(OrderManager):
    def is_order_acceptable(self, order: Order):

        return not bool(self.order_list.last_order)
