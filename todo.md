broker.events не должен принимать kline, надо брать из внутренних данных

вытащить брокер из ордер-менеджера

подвинуть в Order
get_trade_close_type
get_trade_open_type

стратегию переименовать в find_local_trade_opportunity или вроде того
возвр OrderRequest ? или TradeRequest

найти место для get_moving_window_iterator

def get_logger() - хранит синглетон логгера в замыкании

close_order_by_xxx - возвращать новый ордер вместо мутирования старого

для всех ценников использовать тип Price = Union[int, Decimal]

level - dataclass

tradingview.js - в закрытой репе, нужно слать запрос
chart.js - открытый, строит графики свечей, можно добавлять графики индикаторов, см multi chart
