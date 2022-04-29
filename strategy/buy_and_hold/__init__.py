from typing import Tuple

from .emitter import ConstantEmitter
from .ordermanager import HoldOrderManager
from ..emitter import SignalEmitter


def init_context() -> Tuple[HoldOrderManager, SignalEmitter]:
    return HoldOrderManager(), ConstantEmitter()
