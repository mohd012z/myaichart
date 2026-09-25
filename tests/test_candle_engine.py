from datetime import datetime, timezone
from myaichart.candles.engine import CandleEngine
from myaichart.models import NormalizedTick, CandleState, BoundaryProfile


def mk(minute, sec, bid, ask, rid, received=None):
    ts = datetime(2026, 9, 25, 7, minute, sec, tzinfo=timezone.utc)
    return NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id=rid,
        source_timestamp_utc=ts, received_timestamp_utc=received or ts,
        bid=bid, ask=ask,
    )


def test_live_candle_uses_real_ticks_only():
    e = CandleEngine(['M5'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2)
    e.on_tick(mk(40, 1, 10.0, 10.2, '1'))
    e.on_tick(mk(40, 2, 10.5, 10.7, '2'))
    e.on_tick(mk(40, 3, 9.8, 10.0, '3'))
    c = e.current('M5')
    assert c.bid_open == 10.0
    assert c.bid_high == 10.5
    assert c.bid_low == 9.8
    assert c.bid_close == 9.8
    assert c.mid_high == 10.6
    assert c.tick_count == 3
    assert c.state == CandleState.LIVE


def test_no_tick_does_not_create_flat_candle():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2)
    e.advance_clock(datetime(2026, 9, 25, 7, 42, tzinfo=timezone.utc))
    assert e.current('M1') is None


def test_late_tick_inside_grace_updates_previous_bucket():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2)
    e.on_tick(mk(40, 1, 10, 10.2, 'a'))
    e.advance_clock(datetime(2026, 9, 25, 7, 41, 1, tzinfo=timezone.utc))
    received = datetime(2026, 9, 25, 7, 41, 1, tzinfo=timezone.utc)
    late = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='late',
        source_timestamp_utc=datetime(2026, 9, 25, 7, 40, 59, 900000, tzinfo=timezone.utc),
        received_timestamp_utc=received, bid=11, ask=11.2,
    )
    e.on_tick(late)
    assert e.previous('M1').bid_high == 11
    assert e.previous('M1').state == CandleState.PROVISIONALLY_CLOSED


def test_post_finalization_backfill_creates_revision_not_silent_mutation():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2)
    e.on_tick(mk(40, 1, 10, 10.2, 'a'))
    e.advance_clock(datetime(2026, 9, 25, 7, 41, 3, tzinfo=timezone.utc))
    finalized = e.previous('M1')
    correction = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='corr',
        source_timestamp_utc=datetime(2026, 9, 25, 7, 40, 30, tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026, 9, 25, 7, 42, 0, tzinfo=timezone.utc),
        bid=12, ask=12.2,
    )
    revision = e.apply_authorized_correction(correction, reason='BACKFILL')
    assert finalized.state == CandleState.FINAL
    assert revision.old == finalized
    assert revision.new.bid_high == 12
    assert revision.new.state == CandleState.CORRECTED
    assert revision.old != revision.new
