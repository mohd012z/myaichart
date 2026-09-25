from __future__ import annotations

from collections import defaultdict
from myaichart.candles.bucket import bucket_bounds
from myaichart.models import Candle, CandleState


def aggregate_candles(candles, timeframe, profile, *, source_offset_minutes=0):
    groups=defaultdict(list)
    for candle in sorted(candles, key=lambda x:x.time_open_utc):
        start,end=bucket_bounds(candle.time_open_utc,timeframe,profile,source_offset_minutes=source_offset_minutes)
        groups[(start,end)].append(candle)
    out=[]
    for (start,end), group in sorted(groups.items()):
        out.append(_aggregate_group(start,end,group,timeframe,profile))
    return out


def _aggregate_group(start,end,group,timeframe,profile):
    first,last=group[0],group[-1]
    return Candle(
        symbol=first.symbol,timeframe=timeframe,boundary_profile=profile,
        time_open_utc=start,time_close_utc=end,state=CandleState.FINAL,
        bid_open=first.bid_open,bid_high=max(c.bid_high for c in group),bid_low=min(c.bid_low for c in group),bid_close=last.bid_close,
        ask_open=first.ask_open,ask_high=max(c.ask_high for c in group),ask_low=min(c.ask_low for c in group),ask_close=last.ask_close,
        mid_open=first.mid_open,mid_high=max(c.mid_high for c in group),mid_low=min(c.mid_low for c in group),mid_close=last.mid_close,
        tick_count=sum(c.tick_count for c in group),quote_change_count=sum(c.quote_change_count for c in group),
    )
