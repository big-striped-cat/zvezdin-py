import logging
from datetime import date, datetime

import click

from backtest import backtest_strategy
from broker import BrokerSimulator, KlineDataRange
from strategy import Trend

logging.basicConfig(level=logging.INFO)


logger = logging.getLogger(__name__)


@click.group()
def cli():
    pass


@cli.command()
@click.option('--from', 'date_from', type=click.DateTime(), required=True, help='date from')
@click.option('--to', 'date_to', type=click.DateTime(), required=True, help='date to')
def backtest(date_from: datetime, date_to: datetime):
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
    broker = BrokerSimulator(kline_data_range=kline_data_range)

    global_trend = Trend.DOWN

    backtest_strategy(global_trend, broker)


if __name__ == '__main__':
    cli()
