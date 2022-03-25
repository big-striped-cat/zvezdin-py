убрать логику определения цены закрытия из order manager

BrokerSimulator вынести в отдельный модуль
пакет broker

broker.events не должен принимать kline, надо брать из внутренних данных

подвинуть в Order
get_trade_close_type
get_trade_open_type

стратегию переименовать в find_local_trade_opportunity или вроде того
возвр OrderRequest ? или TradeRequest

добавить TradingContextLocal и TradingContextGlobal
хранят уровни и ключевые события

найти место для get_moving_window_iterator

close_order_by_xxx - возвращать новый ордер вместо мутирования старого

для всех ценников использовать тип Price = Union[int, Decimal]

level - dataclass

tradingview.js - в закрытой репе, нужно слать запрос
chart.js - открытый, строит графики свечей, можно добавлять графики индикаторов, см multi chart
