from datetime import datetime, timezone
from myaichart.models import NormalizedTick, BoundaryProfile
from myaichart.candles.from_ticks import build_tick_candles


def t(rid, minute, sec, bid, ask):
    ts=datetime(2026,9,25,7,minute,sec,tzinfo=timezone.utc)
    return NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id=rid,
        source_timestamp_utc=ts,received_timestamp_utc=ts,bid=bid,ask=ask)


def test_build_tick_candles_creates_observed_bars_only():
    ticks=[t('a',40,1,10,10.2),t('b',40,30,11,11.2),t('c',42,1,9,9.2)]
    out=build_tick_candles(ticks,['M1'],BoundaryProfile.MYT_CALENDAR)
    bars=out['M1']
    assert len(bars)==2
    assert bars[0].bid_open==10
    assert bars[0].bid_high==11
    assert bars[0].bid_low==10
    assert bars[0].bid_close==11
    assert bars[0].tick_count==2
    assert bars[1].time_open_utc.minute==42


def test_build_tick_candles_builds_multiple_timeframes_from_same_ticks():
    ticks=[t('a',40,1,10,10.2),t('b',44,30,11,11.2),t('c',45,1,12,12.2)]
    out=build_tick_candles(ticks,['M1','M5'],BoundaryProfile.MYT_CALENDAR)
    assert len(out['M1'])==3
    assert len(out['M5'])==2
    assert out['M5'][0].bid_open==10
    assert out['M5'][0].bid_close==11
