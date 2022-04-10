from decimal import Decimal

from orderlist import OrderList


class TestOrderList:
    def test_profit(self):
        order_list = OrderList()
        assert order_list.profit() == Decimal()
