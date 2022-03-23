import csv
import enum
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Iterator, Optional

import pytz

from kline import Kline
from order import Order, OrderId


class BrokerEventType(enum.Enum):
    order_open = 1
    order_close = 2
    order_close_by_take_profit = 3
    order_close_by_stop_loss = 4


@dataclass
class BrokerEvent:
    order_id: OrderId
    type: BrokerEventType
    created_at: datetime
    price: Decimal


class Broker:
    def klines(self) -> Iterator[Kline]:
        raise NotImplemented

    def add_order(self, order: Order) -> BrokerEvent:
        raise NotImplemented

    def events(self, kline) -> list[BrokerEvent]:
        raise NotImplemented

    def close_order(self, order_id: OrderId, kline: Kline) -> BrokerEvent:
        raise NotImplemented


class BrokerSimulator(Broker):
    def __init__(
        self,
        klines_csv_path: Optional[str] = None,
        kline_data_range: Optional['KlineDataRange'] = None
    ):
        assert klines_csv_path or kline_data_range
        path_iter = (klines_csv_path,) if klines_csv_path else kline_data_range.path_iter()

        self._klines = get_klines_iter(
            path_iter,
            skip_header=False,
            timeframe=timedelta(minutes=5)
        )

        self.order_count = 0
        self.orders: dict[OrderId, Order] = {}

    def klines(self) -> Iterator[Kline]:
        return self._klines

    def add_order(self, order: Order) -> BrokerEvent:
        self.order_count += 1
        order_id = self.order_count
        self.orders[order_id] = order

        return BrokerEvent(
            order_id=order_id,
            type=BrokerEventType.order_open,
            created_at=order.trade_open.created_at,
            price=order.trade_open.price
        )

    def events(self, kline) -> list[BrokerEvent]:
        events = []

        for order_id in self.orders.keys():
            if event := self.wait_for_order_event(kline, order_id):
                events.append(event)

        for event in events:
            if event.type in (
                BrokerEventType.order_close_by_take_profit,
                BrokerEventType.order_close_by_stop_loss,
            ) and event.order_id in self.orders:
                del self.orders[event.order_id]

        return events

    def wait_for_order_event(self, kline: Kline, order_id: OrderId) -> Optional[BrokerEvent]:
        order = self.orders[order_id]

        if is_take_profit_achieved(kline, order) and is_stop_loss_achieved(kline, order):
            raise Exception('Undefined behaviour. Take profit and stop loss both achieved.')

        if is_take_profit_achieved(kline, order):
            return BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_take_profit,
                created_at=kline.open_time,
                price=order.price_take_profit
            )

        if is_stop_loss_achieved(kline, order):
            return BrokerEvent(
                order_id=order_id,
                type=BrokerEventType.order_close_by_stop_loss,
                created_at=kline.open_time,
                price=order.price_stop_loss
            )

    def close_order(self, order_id: OrderId, kline: Kline) -> BrokerEvent:
        self.orders.pop(order_id)

        return BrokerEvent(
            order_id=order_id,
            type=BrokerEventType.order_close,
            created_at=kline.open_time,
            price=kline.open
        )


@dataclass
class KlineDataRange:
    path_template: str
    date_from: date
    date_to: date

    def path_iter(self) -> Iterator[str]:
        for d in date_iter(self.date_from, self.date_to):
            yield d.strftime(self.path_template)


def get_klines_iter(
        path_iter: Iterator[str],
        skip_header: bool = False,
        timeframe: timedelta = timedelta()
) -> Iterator[Kline]:
    for path in path_iter:
        yield from read_klines_from_csv(path, skip_header=skip_header, timeframe=timeframe)


def date_iter(date_from: date, date_to: date) -> Iterator[date]:
    d = date_from
    while d <= date_to:
        yield d
        d += timedelta(days=1)


def read_klines_from_csv(
        path: str,
        skip_header: bool = False,
        timeframe: timedelta = timedelta()
        ) -> list[Kline]:
    res = []
    field_names = ['open_time', 'open', 'high', 'low', 'close', 'volume']

    with open(path) as f:
        if skip_header:
            next(f)
        reader = csv.DictReader(f, fieldnames=field_names)
        for row in reader:
            open_time = datetime.fromtimestamp(int(row['open_time']) / 1000, tz=pytz.UTC)

            # close_time in Binance market data looks like 1642637099999, which is next kline open time minus 1ms.
            # This is not nice time for logging.
            # Better to construct close_time manually
            close_time = open_time + timeframe

            open_price = Decimal(row['open'])  # do not clash with `open` python keyword
            high = Decimal(row['high'])
            low = Decimal(row['low'])
            close = Decimal(row['close'])
            volume = Decimal(row['volume'])

            res.append(Kline(
                open_time=open_time,
                close_time=close_time,
                open=open_price,
                high=high,
                low=low,
                close=close,
                volume=volume
            ))

    return res


def is_price_achieved(kline: Kline, price: Decimal) -> bool:
    return kline.low <= price <= kline.high


def is_take_profit_achieved(kline: Kline, order: Order) -> bool:
    return is_price_achieved(kline, order.price_take_profit)


def is_stop_loss_achieved(kline: Kline, order: Order) -> bool:
    return is_price_achieved(kline, order.price_stop_loss)
