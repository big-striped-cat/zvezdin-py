# Trading Platform

## In general 

The platform is supposed for backtesting and running trading strategies.

## Configuring a strategy

First create global config:

```shell
cp config.example.yml config.yml
```

Strategies are located in strategy/ dir. There are some built-in strategies:

* buy-and-hold strategy. Can be configured to sell and hold also.
* levels-v1. Calculates price levels and makes trade when price jumps off the level.

Example config included for each strategy. See config.example.yml. 
To run strategy you need to create actual config:

```shell
cd strategy/<name>
cp config.example.yml config.yml
```

## Commands

Download Binance kline (candle) data for given ticker and date:

```shell
./binance-download.sh BTCBUSD-5m-2022-02-26
```

Kline data is downloaded into market_data/ folder. 

Run backtests for a strategy:

```shell
python app.py backtest --strategy buy-and-hold --from 2022-02-18 --to 2022-02-26
```

Run backtests with a custom window size:
```shell
python app.py backtest --strategy levels-v1 --from 2022-02-18 --to 2022-02-26 --window 100
```

## Development

Running tests

```shell
pytest .
```

For visualization purposes some xlsx charts are located in `test_data/levels`.
There are price charts for small periods of time.
Those charts help to understand existing tests and write new ones.
Files are named the same as tests.

Note. The price in `market_data/*.csv` files may be a little different from the price you see on exchanges.
