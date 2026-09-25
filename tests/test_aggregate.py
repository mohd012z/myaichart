from datetime import datetime, timedelta, timezone
from myaichart.candles.aggregate import aggregate_candles
from myaichart.models import BoundaryProfile, Candle, CandleState


def c(ts, px):
    return Candle(
        symbol='XAUUSD', timeframe='M1', boundary_profile=BoundaryProfile.MYT_CALENDAR,
        time_open_utc=ts, time_close_utc=ts+timedelta(minutes=1), state=CandleState.FINAL,
        bid_open=px, bid_high=px+0.4, bid_low=px-0.2, bid_close=px+0.1,
        ask_open=px+0.1, ask_high=px+0.5, ask_low=px-0.1, ask_close=px+0.2,
        mid_open=px+0.05, mid_high=px+0.45, mid_low=px-0.15, mid_close=px+0.15,
        tick_count=10, quote_change_count=9,
    )


def test_higher_frame_ohlc_uses_first_max_min_last():
    base=datetime(2026,9,25,7,40,tzinfo=timezone.utc)
    fixture=[c(base+timedelta(minutes=i), 10+i) for i in range(5)]
    out=aggregate_candles(fixture,'M5',BoundaryProfile.MYT_CALENDAR)
    assert len(out)==1
    assert out[0].mid_open == fixture[0].mid_open
    assert out[0].mid_high == max(x.mid_high for x in fixture)
    assert out[0].mid_low == min(x.mid_low for x in fixture)
    assert out[0].mid_close == fixture[-1].mid_close
    assert out[0].tick_count == 50


def test_myt_daily_and_source_session_daily_can_differ():
    fixture=[c(datetime(2026,9,24,15,59,tzinfo=timezone.utc),10), c(datetime(2026,9,24,16,1,tzinfo=timezone.utc),11)]
    myt=aggregate_candles(fixture,'D1',BoundaryProfile.MYT_CALENDAR)
    src=aggregate_candles(fixture,'D1',BoundaryProfile.SOURCE_SESSION,source_offset_minutes=120)
    assert len(myt)==2
    assert len(src)==1
    assert myt[0].time_open_utc != src[0].time_open_utc
