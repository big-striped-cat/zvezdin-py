from datetime import timedelta

from strategy.utils import parse_timedelta


def test_parse_timedelta():
    assert parse_timedelta("5m") == timedelta(minutes=5)
    assert parse_timedelta("8h") == timedelta(hours=8)
