from datetime import datetime
from decimal import Decimal

from order import Trade, TradeType, Order, OrderType


def trade_factory(trade_type=None, price=None, amount=None, created_at=None) -> Trade:
    trade_type = trade_type or TradeType.BUY
    price = price or Decimal()
    amount = amount or Decimal(1)
    created_at = created_at or datetime(2022, 1, 1)

    return Trade(type=trade_type, price=price, amount=amount, created_at=created_at)


def order_factory(
    order_type=None,
    trade_open=None,
    trade_close=None,
    level=None,
    price_take_profit=None,
    price_stop_loss=None,
    auto_close_in=None,
) -> Order:
    order_type = order_type or OrderType.LONG
    trade_open = trade_open or trade_factory()
    level = level or (Decimal(), Decimal())
    price_take_profit = price_take_profit or Decimal()
    price_stop_loss = price_stop_loss or Decimal()

    return Order(
        order_type=order_type,
        trade_open=trade_open,
        trade_close=trade_close,
        level=level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss,
        auto_close_in=auto_close_in,
    )
