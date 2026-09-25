from datetime import datetime, timedelta, timezone
import pytest
from myaichart.candles.engine import CandleEngine
from myaichart.live.replay import ReplayAdapter
from myaichart.models import BoundaryProfile, NormalizedTick


def ticks():
    base=datetime(2026,9,25,7,40,tzinfo=timezone.utc)
    out=[]
    for i,(b,a) in enumerate([(10,10.2),(10.5,10.7),(9.8,10.0),(11,11.2)]):
        ts=base+timedelta(seconds=i*30)
        out.append(NormalizedTick(symbol='XAUUSD',source='fixture',source_record_id=str(i),source_timestamp_utc=ts,received_timestamp_utc=ts,bid=b,ask=a))
    return out


@pytest.mark.asyncio
async def test_identical_tick_sequence_produces_identical_candles():
    seq=ticks()
    live=CandleEngine(['M1','M5'],BoundaryProfile.MYT_CALENDAR,grace_seconds=2)
    for t in seq: live.on_tick(t)
    live.advance_clock(datetime(2026,9,25,7,45,3,tzinfo=timezone.utc))

    replay=CandleEngine(['M1','M5'],BoundaryProfile.MYT_CALENDAR,grace_seconds=2)
    async for t in ReplayAdapter(seq,speed=50).stream(): replay.on_tick(t)
    replay.advance_clock(datetime(2026,9,25,7,45,3,tzinfo=timezone.utc))
    assert replay.finalized('M5')==live.finalized('M5')
    assert replay.finalized('M1')==live.finalized('M1')
