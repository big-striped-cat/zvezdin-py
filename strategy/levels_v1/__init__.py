from typing import Tuple

from .config_parser import parse_config
from .emitter import JumpLevelEmitter
from .ordermanager import DeduplicateOrderManager
from ..emitter import SignalEmitter
from ..ordermanager import OrderManager


def init_context() -> Tuple[OrderManager, SignalEmitter]:
    config_path = 'strategy/levels_v1/config.yml'
    return parse_config(config_path)
