import logging
from datetime import datetime
from typing import Tuple

import click
from yaml import load, Loader

from backtest import backtest_strategy
from broker import BrokerSimulator, KlineDataRange

from strategy.ordermanager import OrderManager
from strategy.emitter import SignalEmitter

logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


def init_strategy_context(strategy_name) -> Tuple[OrderManager, SignalEmitter]:
    pkg = {
        'buy-and-hold': 'strategy.buy_and_hold',
        'sell-and-hold': 'strategy.sell_and_hold',
        'levels-v1': 'strategy.levels_v1',
    }[strategy_name]
    imp = __import__(pkg, globals(), locals(), ['init_context'])
    return imp.init_context()


@cli.command()
@click.option('--strategy', required=True, help='strategy name')
@click.option('--from', 'date_from', type=click.DateTime(), required=True, help='date from')
@click.option('--to', 'date_to', type=click.DateTime(), required=True, help='date to')
def backtest(strategy: str, date_from: datetime, date_to: datetime):
    # path = 'market_data/BTCBUSD-5m-2022-02-18.csv'
    path_template = 'market_data/BTCBUSD-5m-%Y-%m-%d.csv'
    date_from = date_from.date()
    date_to = date_to.date()

    logger.info('date_from %s', date_from)
    logger.info('date_to %s', date_to)

    kline_data_range = KlineDataRange(
        path_template=path_template,
        date_from=date_from,
        date_to=date_to
    )

    with open('config.yml') as f:
        configs = load(f, Loader=Loader)

    broker = BrokerSimulator(
        kline_data_range=kline_data_range,
        config=configs.get('broker', {}).get('simulator', {})
    )

    context_global, context_local = init_strategy_context(strategy)
    backtest_strategy(context_global, context_local, broker)


if __name__ == '__main__':
    cli()
