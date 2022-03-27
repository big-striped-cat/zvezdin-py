import re
from datetime import timedelta
from decimal import Decimal
from typing import Optional

from strategy import Trend


def parse_timedelta(delta: str) -> Optional[timedelta]:
    match = re.match('^(\d+)m$', delta)
    if match:
        minutes = int(match.group(1))
        return timedelta(minutes=minutes)


def parse_trading_context_global_config(config: dict):
    return {
        'trend': Trend[config['trend'].upper()],
        'levels_intersection_threshold': Decimal(config['levels_intersection_threshold']),
        'order_intersection_timeout': parse_timedelta(config['order_intersection_timeout']),
        'price_open_to_level_ratio_threshold': Decimal(config['price_open_to_level_ratio_threshold']),
    }
