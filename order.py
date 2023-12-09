import enum
import logging
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, Union, List

from datetime import timedelta

from kline import Kline
from lib.levels import Level

logger = logging.getLogger(__name__)


class OrderType(enum.Enum):
    LONG = 1
    SHORT = 2

    @property
    def sign(self) -> int:
        return {
            OrderType.LONG: 1,
            OrderType.SHORT: -1,
        }[self]

    def __str__(self):
        return {
            OrderType.LONG: "long",
            OrderType.SHORT: "short",
        }[self]


class TradeType(enum.Enum):
    BUY = 1
    SELL = 2

    def __str__(self):
        return {
            TradeType.BUY: "buy",
            TradeType.SELL: "sell",
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
    id: Optional[int]
    order_type: OrderType
    amount: Decimal
    trade_open: Trade
    trade_close: Optional[Trade]
    level: Level
    price_stop_loss: Decimal
    auto_close_in: Optional[timedelta]
    sub_orders: List["SubOrder"]

    def get_profit(self, close_price: Optional[Decimal] = None) -> Decimal:
        if self.trade_close and close_price is None:
            close_price = self.trade_close.price

        return sum(
            (
                sub_order.get_profit(self.trade_open.price, close_price)
                for sub_order in self.sub_orders
            ),
            Decimal(),
        )

    def get_profit_unrealized(self, price: Decimal) -> Decimal:
        return self.get_profit(close_price=price)

    @property
    def is_closed(self) -> bool:
        if self.trade_close is not None:
            return True

        return all([sub_order.is_closed for sub_order in self.sub_orders])


@dataclass
class SubOrder:
    order_type: OrderType
    amount: Decimal
    price_take_profit: Decimal
    next_price_stop_loss: Optional[Decimal] = None
    trade_close: Optional[Trade] = None

    @property
    def sign(self) -> int:
        return {
            OrderType.LONG: 1,
            OrderType.SHORT: -1,
        }[self.order_type]

    def get_profit(
        self, open_price: Decimal, close_price: Optional[Decimal] = None
    ) -> Decimal:
        if self.trade_close is None and close_price is None:
            raise ValueError("trade_close attr or close_price param must be set")

        if close_price is None:
            close_price = self.trade_close.price  # type: ignore

        profit = self.order_type.sign * (close_price - open_price) * self.amount
        return profit

    @property
    def is_closed(self) -> bool:
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
    order_type: OrderType,
    kline: Kline,
    level: Level,
    amount: Decimal,
    price_stop_loss: Decimal,
    auto_close_in: timedelta,
    sub_orders: list[SubOrder],
) -> Order:
    trade_type = get_trade_open_type(order_type)
    trade_open = None

    if sub_orders is not None:
        trade_open = Trade(
            type=trade_type,
            price=kline.close,
            amount=amount,
            created_at=kline.close_time,
        )

    return Order(
        id=None,
        order_type=order_type,
        amount=amount,
        trade_open=trade_open,
        trade_close=None,
        level=level,
        price_stop_loss=price_stop_loss,
        auto_close_in=auto_close_in,
        sub_orders=sub_orders,
    )


OrderId = Union[int, str]
