from order import Order
from strategy.tradingcontextglobal import TradingContextGlobalBase


class TradingContextGlobal(TradingContextGlobalBase):
    def is_order_acceptable(self, order: Order):

        return not bool(self.order_list.last_order)
