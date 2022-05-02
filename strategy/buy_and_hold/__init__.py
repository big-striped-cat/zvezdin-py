from typing import Tuple

from yaml import load, Loader

from order import OrderType
from .emitter import ConstantEmitter
from .ordermanager import HoldOrderManager
from ..emitter import SignalEmitter
from ..ordermanager import OrderManager


def init_context() -> Tuple[OrderManager, SignalEmitter]:
    with open('strategy/buy_and_hold/config.yml') as f:
        configs = load(f, Loader=Loader)

    order_type_str = configs['emitter']['order_type'].upper()
    order_type = OrderType[order_type_str]

    return HoldOrderManager(), ConstantEmitter(order_type=order_type)
