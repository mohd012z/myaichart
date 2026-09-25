from __future__ import annotations

from dataclasses import dataclass
from myaichart.candles.bucket import bucket_bounds
from myaichart.models import BoundaryProfile, Candle, CandleState, NormalizedTick


@dataclass
class _TickAccumulator:
    symbol: str
    timeframe: str
    profile: BoundaryProfile
    start: object
    end: object
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    mid_open: float
    mid_high: float
    mid_low: float
    mid_close: float
    tick_count: int = 1
    quote_change_count: int = 0

    @classmethod
    def from_tick(cls, tick, timeframe, profile, start, end):
        mid=tick.mid
        return cls(tick.symbol,timeframe,profile,start,end,
            tick.bid,tick.bid,tick.bid,tick.bid,
            tick.ask,tick.ask,tick.ask,tick.ask,
            mid,mid,mid,mid)

    def apply(self, tick):
        if tick.bid != self.bid_close or tick.ask != self.ask_close:
            self.quote_change_count += 1
        self.bid_high=max(self.bid_high,tick.bid); self.bid_low=min(self.bid_low,tick.bid); self.bid_close=tick.bid
        self.ask_high=max(self.ask_high,tick.ask); self.ask_low=min(self.ask_low,tick.ask); self.ask_close=tick.ask
        mid=tick.mid
        self.mid_high=max(self.mid_high,mid); self.mid_low=min(self.mid_low,mid); self.mid_close=mid
        self.tick_count += 1

    def finish(self):
        return Candle(symbol=self.symbol,timeframe=self.timeframe,boundary_profile=self.profile,
            time_open_utc=self.start,time_close_utc=self.end,state=CandleState.FINAL,
            bid_open=self.bid_open,bid_high=self.bid_high,bid_low=self.bid_low,bid_close=self.bid_close,
            ask_open=self.ask_open,ask_high=self.ask_high,ask_low=self.ask_low,ask_close=self.ask_close,
            mid_open=self.mid_open,mid_high=self.mid_high,mid_low=self.mid_low,mid_close=self.mid_close,
            tick_count=self.tick_count,quote_change_count=self.quote_change_count)


def build_tick_candles(ticks, timeframes, profile: BoundaryProfile, *, source_offset_minutes=0):
    """Build observed candles from an already source-time-ordered tick stream."""
    frames=tuple(timeframes)
    out={tf:[] for tf in frames}
    active={}
    previous_ts=None
    for tick in ticks:
        ts=tick.source_timestamp_utc
        if previous_ts is not None and ts < previous_ts:
            raise ValueError('tick stream must be ordered by source timestamp')
        previous_ts=ts
        for tf in frames:
            start,end=bucket_bounds(ts,tf,profile,source_offset_minutes=source_offset_minutes)
            acc=active.get(tf)
            if acc is None:
                active[tf]=_TickAccumulator.from_tick(tick,tf,profile,start,end)
            elif start == acc.start:
                acc.apply(tick)
            elif start > acc.start:
                out[tf].append(acc.finish())
                active[tf]=_TickAccumulator.from_tick(tick,tf,profile,start,end)
            else:
                raise ValueError('tick moved backwards across candle bucket')
    for tf,acc in active.items():
        out[tf].append(acc.finish())
    return out
