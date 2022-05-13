from typing import Tuple

from yaml import load, Loader

from orderlist import OrderList
from strategy.levels_v1.emitter import JumpLevelEmitter
from strategy.levels_v1.ordermanager import DeduplicateOrderManager
from .emitter import JumpLevelEmitter
from .ordermanager import DeduplicateOrderManager
from ..emitter import SignalEmitter
from ..ordermanager import OrderManager


def init_context() -> Tuple[OrderManager, SignalEmitter]:
    path = 'strategy/levels_v1/config.yml'

    with open(path) as f:
        configs = load(f, Loader=Loader)

    return (
        DeduplicateOrderManager(OrderList(), **configs['order_manager']),
        JumpLevelEmitter(**configs['emitter'])
    )
