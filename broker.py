import csv
import enum
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta, datetime
from decimal import Decimal
from typing import Iterator, Optional, List

from localbroker import LocalOrderUpdate
from utils import format_datetime

import pytz

from kline import Kline
from order import Order, OrderId, SubOrder

logger = logging.getLogger(__name__)


class BrokerEventType(enum.Enum):
    order_open = 1
    order_close = 2
    order_close_by_take_profit = 3
    order_close_by_stop_loss = 4
    sub_order_close_by_take_profit = 5


@dataclass
class BrokerEvent:
    order_id: OrderId
    sub_order_index: Optional[int]
    type: BrokerEventType
    created_at: datetime
    price: Decimal


class Broker:
    def klines(self) -> Iterator[Kline]:
        raise NotImplemented

    def submit_order(self, order: Order) -> BrokerEvent:
        raise NotImplemented

    def events(self, kline) -> dict[OrderId, list[BrokerEvent]]:
        """
        :return: events must be ordered by time in ascending order
        """
        raise NotImplemented

    def close_order(self, order_id: OrderId, kline: Kline) -> BrokerEvent:
        raise NotImplemented

    def update_order(self, order_update: LocalOrderUpdate) -> None:
        raise NotImplemented


class BrokerSimulator(Broker):
    def __init__(
        self,
        klines_csv_path: Optional[str] = None,
        kline_data_range: Optional["KlineDataRange"] = None,
        config=None,
    ):
        if klines_csv_path:
            path_iter = iter((klines_csv_path,))
        elif kline_data_range:
            path_iter = kline_data_range.path_iter()
        else:
            raise ValueError("Provide klines_csv_path or kline_data_range")

        self.config = config or {}

        self._klines = get_klines_iter(
            path_iter,
            skip_header=self.config.get("skip_header", True),
            timeframe=timedelta(minutes=5),
        )

        self.order_count = 0
        self.orders: dict[OrderId, Order] = {}

    def klines(self) -> Iterator[Kline]:
        return self._klines

    def submit_order(self, order: Order) -> BrokerEvent:
        self.order_count += 1
        order_id = self.order_count
        self.orders[order_id] = order

        event = BrokerEvent(
            order_id=order_id,
            sub_order_index=None,
            type=BrokerEventType.order_open,
            created_at=order.trade_open.created_at,
            price=order.trade_open.price,
        )

        return event

    def events(self, kline) -> dict[OrderId, list[BrokerEvent]]:
        events = defaultdict(lambda: [])

        for order_id, order in self.orders.items():
            for sub_order_index in range(len(order.sub_orders)):
                events[order_id].extend(
                    self.wait_for_order_event(kline, order_id, sub_order_index)
                )

        for order_events in events.values():
            for event in order_events:
                if (
                    event.type
                    in (
                        BrokerEventType.order_close_by_take_profit,
                        BrokerEventType.order_close_by_stop_loss,
                    )
                    and event.order_id in self.orders
                ):
                    del self.orders[event.order_id]

        return events

    def wait_for_order_event(
        self, kline: Kline, order_id: OrderId, sub_order_index: int
    ) -> List[BrokerEvent]:
        order = self.orders[order_id]
        sub_order = order.sub_orders[sub_order_index]

        if is_take_profit_achieved(kline, sub_order) and is_stop_loss_achieved(
            kline, order
        ):
            logger.warning(
                "Undefined behaviour for order %s. Take profit and stop loss both achieved.",
                order_id,
            )
            logger.info(
                "take_profit_stop_loss_both_achieved strategy: %s",
                self.config.get("take_profit_stop_loss_both_achieved"),
            )

            if (
                self.config.get("take_profit_stop_loss_both_achieved")
                == "close_by_stop_loss"
            ):
                return [
                    BrokerEvent(
                        order_id=order_id,
                        sub_order_index=sub_order_index,
                        type=BrokerEventType.order_close_by_stop_loss,
                        created_at=kline.open_time,
                        price=order.price_stop_loss,
                    )
                ]
            raise Exception(
                "Undefined behaviour. Take profit and stop loss both achieved."
            )

        if is_stop_loss_achieved(kline, order):
            return [
                BrokerEvent(
                    order_id=order_id,
                    sub_order_index=None,
                    type=BrokerEventType.order_close_by_stop_loss,
                    created_at=kline.open_time,
                    price=order.price_stop_loss,
                )
            ]

        events = []

        if is_take_profit_achieved(kline, sub_order):
            events.append(
                BrokerEvent(
                    order_id=order_id,
                    sub_order_index=sub_order_index,
                    type=BrokerEventType.sub_order_close_by_take_profit,
                    created_at=kline.open_time,
                    price=sub_order.price_take_profit,
                )
            )
            if sub_order_index == len(order.sub_orders) - 1:
                # `order.is_closed` is still False at this moment
                # but the order is closed on remote broker side
                del self.orders[order_id]

        return events

    def update_order(self, order_update: LocalOrderUpdate) -> None:
        order = self.orders[order_update.order_id]
        order.price_stop_loss = order_update.price_stop_loss

    def close_order(self, order_id: OrderId, kline: Kline) -> BrokerEvent:
        event = BrokerEvent(
            order_id=order_id,
            sub_order_index=None,
            type=BrokerEventType.order_close,
            created_at=kline.open_time,
            price=kline.open,
        )
        self.orders.pop(order_id)

        return event


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
    timeframe: timedelta = timedelta(),
) -> Iterator[Kline]:
    for path in path_iter:
        yield from read_klines_from_csv(
            path, skip_header=skip_header, timeframe=timeframe
        )


def date_iter(date_from: date, date_to: date) -> Iterator[date]:
    d = date_from
    while d <= date_to:
        yield d
        d += timedelta(days=1)


def read_klines_from_csv(
    path: str, skip_header: bool = False, timeframe: timedelta = timedelta()
) -> list[Kline]:
    res = []
    field_names = ["open_time", "open", "high", "low", "close", "volume"]

    with open(path) as f:
        if skip_header:
            next(f)
        reader = csv.DictReader(f, fieldnames=field_names)
        for row in reader:
            open_time = datetime.fromtimestamp(
                int(row["open_time"]) / 1000, tz=pytz.UTC
            )

            # close_time in Binance market data looks like 1642637099999, which is next kline open time minus 1ms.
            # This is not nice time for logging.
            # Better to construct close_time manually
            close_time = open_time + timeframe

            open_price = Decimal(row["open"])  # do not clash with `open` python keyword
            high = Decimal(row["high"])
            low = Decimal(row["low"])
            close = Decimal(row["close"])
            volume = Decimal(row["volume"])

            res.append(
                Kline(
                    open_time=open_time,
                    close_time=close_time,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )

    return res


def is_price_achieved(kline: Kline, price: Decimal) -> bool:
    return kline.low <= price <= kline.high


def is_take_profit_achieved(kline: Kline, sub_order: SubOrder) -> bool:
    return is_price_achieved(kline, sub_order.price_take_profit)


def is_stop_loss_achieved(kline: Kline, order: Order) -> bool:
    return is_price_achieved(kline, order.price_stop_loss)
