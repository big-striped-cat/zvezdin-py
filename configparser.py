import re
from datetime import timedelta
from decimal import Decimal
from typing import Optional, Tuple
from yaml import load, Loader

from ordermanager import OrderList
from tradingcontextglobal import TradingContextGlobal
from tradingcontextlocal import TradingContextLocal
from trend import Trend


def parse_timedelta(delta: str) -> Optional[timedelta]:
    match = re.match('^(\d+)m$', delta)
    if match:
        minutes = int(match.group(1))
        return timedelta(minutes=minutes)


def convert_trading_context_global_config(config: dict) -> dict:
    """
    :param config: dict with values of generic python types: int, str
    :return: dict with values of application-specific types: Decimal, timedelta, class instances, etc
    """
    return {
        'trend': Trend[config['trend'].upper()],
        'levels_intersection_threshold': Decimal(config['levels_intersection_threshold']),
        'order_intersection_timeout': parse_timedelta(config['order_intersection_timeout']),
    }


def convert_trading_context_local_config(config: dict) -> dict:
    """
    :param config: dict with values of generic python types: int, str
    :return: dict with values of application-specific types: Decimal, timedelta, class instances, etc
    """
    return {
        'price_open_to_level_ratio_threshold': Decimal(config['price_open_to_level_ratio_threshold']),
    }


def parse_config(path) -> Tuple[TradingContextGlobal, TradingContextLocal]:
    with open(path) as f:
        configs = load(f, Loader=Loader)
    trading_context_global_config = convert_trading_context_global_config(
        configs['trading_context']['global']
    )
    trading_context_local_config = convert_trading_context_local_config(
        configs['trading_context']['local']
    )
    return (
        TradingContextGlobal(OrderList(), **trading_context_global_config),
        TradingContextLocal(**trading_context_local_config)
    )
