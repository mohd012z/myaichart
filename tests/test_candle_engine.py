from datetime import datetime, timedelta, timezone
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


def _minute_tick(minute: int, rid: str, bid: float = 10.0):
    ts = datetime(2026, 9, 25, 7, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
    return NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id=rid,
        source_timestamp_utc=ts, received_timestamp_utc=ts,
        bid=bid, ask=bid + 0.2,
    )


def test_closed_retention_is_bounded():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2, max_closed=8)
    for m in range(200):
        e.on_tick(_minute_tick(m, str(m), bid=10.0 + (m % 5)))
    # 200 one-tick minutes = 199 closed buckets (last minute is still active)
    assert len(e._closed['M1']) == 8
    assert e.retention_overflow == 191
    # the retained window is the most recent eight closed buckets
    assert e._closed['M1'][0].accumulator.start == datetime(2026, 9, 25, 10, 11, tzinfo=timezone.utc)
    assert e._closed['M1'][-1].accumulator.start == datetime(2026, 9, 25, 10, 18, tzinfo=timezone.utc)
    assert len(e.all_closed('M1')) == 8


def test_prune_keeps_latest_for_grace_updates():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2, max_closed=4)
    for m in range(60):
        e.on_tick(_minute_tick(m, str(m)))
    # late tick, inside grace, for the most recent closed bucket (07:58) -> still applied
    late = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='late',
        source_timestamp_utc=datetime(2026, 9, 25, 7, 58, 59, 500000, tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026, 9, 25, 7, 59, 1, tzinfo=timezone.utc),
        bid=99, ask=99.2,
    )
    e.on_tick(late)
    assert e.previous('M1').bid_high == 99


def test_correction_outside_retention_window_fails_closed():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2, max_closed=4)
    for m in range(60):
        e.on_tick(_minute_tick(m, str(m)))
    # a correction for a long-evicted bucket must not silently no-op
    evicted = NormalizedTick(
        symbol='XAUUSD', source='fixture', source_record_id='evicted',
        source_timestamp_utc=datetime(2026, 9, 25, 7, 0, 30, tzinfo=timezone.utc),
        received_timestamp_utc=datetime(2026, 9, 25, 8, 3, 0, tzinfo=timezone.utc),
        bid=50, ask=50.2,
    )
    try:
        e.apply_authorized_correction(evicted, reason='BACKFILL')
        raise AssertionError('expected KeyError for evicted bucket')
    except KeyError:
        pass


def test_revision_log_is_bounded():
    e = CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, grace_seconds=2, max_closed=2048)
    e.on_tick(_minute_tick(0, '0'))
    e.advance_clock(datetime(2026, 9, 25, 7, 1, 3, tzinfo=timezone.utc))
    for i in range(1100):
        corr = NormalizedTick(
            symbol='XAUUSD', source='fixture', source_record_id=f'c{i}',
            source_timestamp_utc=datetime(2026, 9, 25, 7, 0, 1, tzinfo=timezone.utc),
            received_timestamp_utc=datetime(2026, 9, 25, 7, 2, 0, tzinfo=timezone.utc),
            bid=10.0 + i, ask=10.2 + i,
        )
        e.apply_authorized_correction(corr, reason='BACKFILL')
    assert len(e.revisions) == 1024


def test_max_closed_below_two_is_rejected():
    try:
        CandleEngine(['M1'], BoundaryProfile.MYT_CALENDAR, max_closed=1)
        raise AssertionError('expected ValueError')
    except ValueError:
        pass
