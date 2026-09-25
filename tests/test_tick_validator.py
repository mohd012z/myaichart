from datetime import datetime, timezone
from myaichart.models import NormalizedTick
from myaichart.live.base import TickValidator
from myaichart.ids import stable_tick_id


def t(record_id, bid, ask, ms=0):
    stamp = datetime(2026, 9, 25, 8, 0, 0, ms * 1000, tzinfo=timezone.utc)
    return NormalizedTick(
        symbol='XAUUSD', source='s', source_record_id=record_id,
        source_timestamp_utc=stamp, received_timestamp_utc=stamp,
        bid=bid, ask=ask,
    )


def test_exact_source_identity_duplicate_is_rejected():
    v = TickValidator()
    assert v.accept(t('a', 1.0, 1.1)).accepted
    assert not v.accept(t('a', 1.0, 1.1)).accepted


def test_equal_timestamp_different_quotes_are_not_collapsed():
    v = TickValidator()
    assert v.accept(t('a', 1.0, 1.1)).accepted
    assert v.accept(t('b', 1.1, 1.2)).accepted


def test_stable_tick_id_is_deterministic():
    assert stable_tick_id('s','a') == stable_tick_id('s','a')
    assert stable_tick_id('s','a') != stable_tick_id('s','b')
