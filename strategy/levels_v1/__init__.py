from typing import Tuple

from .config_parser import parse_config
from .tradingcontextglobal import TradingContextGlobal
from .tradingcontextlocal import TradingContextLocal


def init_context() -> Tuple[TradingContextGlobal, TradingContextLocal]:
    config_path = 'strategy/levels_v1/config.yml'
    return parse_config(config_path)
