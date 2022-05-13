# Trading Platform

## In general 

The platform is supposed for backtesting and running trading strategies.

## Configuring a strategy

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

## Development

Running tests

```shell
pytest .
```
