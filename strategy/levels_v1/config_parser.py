"""
Without underscore this module clashes with built-in 'configparser' module.
"""

import re
from datetime import timedelta
from decimal import Decimal
from typing import Optional, Tuple
from yaml import load, Loader

from ordermanager import OrderList
from strategy.levels_v1.tradingcontextglobal import TradingContextGlobal
from strategy.levels_v1.tradingcontextlocal import TradingContextLocal
from trend import Trend


def parse_timedelta(delta: str) -> Optional[timedelta]:
    match = re.match(r'^(\d+)([m|h])$', delta)
    if not match:
        return

    number = int(match.group(1))
    unit = match.group(2)

    if unit == 'm':
        return timedelta(minutes=number)
    elif unit == 'h':
        return timedelta(hours=number)


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
        'auto_close_in': parse_timedelta(config['auto_close_in'])
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
