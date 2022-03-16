import enum
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union

from kline import Kline
from level import Level
from utils import format_datetime

logger = logging.getLogger(__name__)


class OrderType(enum.Enum):
    LONG = 1
    SHORT = 2

    def __str__(self):
        return {
            OrderType.LONG: 'long',
            OrderType.SHORT: 'short',
        }[self]


class TradeType(enum.Enum):
    BUY = 1
    SELL = 2

    def __str__(self):
        return {
            TradeType.BUY: 'buy',
            TradeType.SELL: 'sell',
        }[self]


@dataclass
class Trade:
    type: TradeType
    price: Decimal
    amount: Decimal
    created_at: datetime

    def value(self):
        return self.price * self.amount


@dataclass
class Order:
    order_type: OrderType
    trade_open: Trade
    trade_close: Optional[Trade]
    level: Level
    price_take_profit: Decimal
    price_stop_loss: Decimal

    def get_profit(self, trade_close: Optional[Trade] = None):
        trade_close = trade_close or self.trade_close
        profit = trade_close.value() - self.trade_open.value()
        return {
            OrderType.LONG: profit,
            OrderType.SHORT: -profit,
        }[self.order_type]

    def get_profit_unrealized(self, price: Decimal):
        trade_close = Trade(
            type=get_trade_close_type(self.order_type),
            price=price,
            amount=self.trade_open.amount,
            created_at=datetime.now()  # dummy time
        )
        return self.get_profit(trade_close=trade_close)

    def is_profit(self):
        return self.get_profit() > 0

    @property
    def is_closed(self):
        return self.trade_close is not None


def get_trade_open_type(order_type: OrderType) -> TradeType:
    return {
        OrderType.LONG: TradeType.BUY,
        OrderType.SHORT: TradeType.SELL,
    }[order_type]


def get_trade_close_type(order_type: OrderType) -> TradeType:
    return {
        OrderType.LONG: TradeType.SELL,
        OrderType.SHORT: TradeType.BUY,
    }[order_type]


def create_order(
        order_type: OrderType, kline: Kline, level: Level,
        price_take_profit=None, price_stop_loss=None,
        ) -> Order:
    price_take_profit = price_take_profit or Decimal()
    price_stop_loss = price_stop_loss or Decimal()

    trade_type = get_trade_open_type(order_type)

    trade_open = Trade(
        type=trade_type,
        price=kline.close,
        amount=Decimal(1),
        created_at=kline.close_time
    )

    return Order(
        order_type=order_type,
        trade_open=trade_open,
        trade_close=None,
        level=level,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss,
    )


def add_percent(d: Decimal, percent: Union[int, Decimal]) -> Decimal:
    if not isinstance(percent, Decimal):
        percent = Decimal(percent)

    res = d * (1 + Decimal('0.01') * percent)
    return Decimal(round(res))


def create_order_long(kline: Kline, level: Level) -> Order:
    price_take_profit = add_percent(kline.close, 2)
    price_stop_loss = add_percent(kline.close, -1)

    return create_order(
        OrderType.LONG, kline, level, logger,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss
    )


def create_order_short(kline: Kline, level: Level) -> Order:
    price_take_profit = add_percent(kline.close, -2)
    price_stop_loss = add_percent(kline.close, 1)

    return create_order(
        OrderType.SHORT, kline, level, logger,
        price_take_profit=price_take_profit,
        price_stop_loss=price_stop_loss
    )


OrderId = Union[int, str]
