
def get_logger() - хранит синглетон логгера в замыкании

close_order_by_xxx - возвращать новый ордер вместо мутирования старого

для всех ценников использовать тип Price = Union[int, Decimal]

обработка ситуации , когда на свечке Take profit and stop loss both achieved 

level - dataclass

вынести уровни в levels.py

tradingview.js - в закрытой репе, нужно слать запрос
chart.js - открытый, строит графики свечей, можно добавлять графики индикаторов, см multi chart
