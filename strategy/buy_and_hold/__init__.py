from typing import Tuple

from .tradingcontextglobal import TradingContextGlobal
from .tradingcontextlocal import TradingContextLocal


def init_context() -> Tuple[TradingContextGlobal, TradingContextLocal]:
    return TradingContextGlobal(), TradingContextLocal()
