#!/bin/bash -e

# Script downloads kline data from https://data.binance.vision/
# Example usage: ./binance-download.sh BTCBUSD-5m-2022-02-26

filename=$1
mkdir -p market_data
curl https://data.binance.vision/data/futures/um/daily/klines/BTCBUSD/5m/${filename}.zip -o ${filename}.zip
unzip -o ${filename}.zip -d market_data
rm ${filename}.zip
