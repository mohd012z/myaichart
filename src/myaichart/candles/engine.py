from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Iterable

from myaichart.candles.bucket import bucket_bounds
from myaichart.candles.revisions import CandleRevision
from myaichart.models import BoundaryProfile, Candle, CandleState, NormalizedTick


@dataclass
class _Accumulator:
    symbol: str
    timeframe: str
    profile: BoundaryProfile
    start: datetime
    end: datetime
    first_bid: float
    high_bid: float
    low_bid: float
    last_bid: float
    first_ask: float
    high_ask: float
    low_ask: float
    last_ask: float
    first_mid: float
    high_mid: float
    low_mid: float
    last_mid: float
    tick_count: int = 1
    quote_change_count: int = 0

    @classmethod
    def from_tick(cls, tick: NormalizedTick, timeframe: str, profile: BoundaryProfile, start: datetime, end: datetime):
        mid = tick.mid
        return cls(
            symbol=tick.symbol,
            timeframe=timeframe,
            profile=profile,
            start=start,
            end=end,
            first_bid=tick.bid,
            high_bid=tick.bid,
            low_bid=tick.bid,
            last_bid=tick.bid,
            first_ask=tick.ask,
            high_ask=tick.ask,
            low_ask=tick.ask,
            last_ask=tick.ask,
            first_mid=mid,
            high_mid=mid,
            low_mid=mid,
            last_mid=mid,
        )

    def apply(self, tick: NormalizedTick):
        if tick.bid != self.last_bid or tick.ask != self.last_ask:
            self.quote_change_count += 1
        self.high_bid = max(self.high_bid, tick.bid)
        self.low_bid = min(self.low_bid, tick.bid)
        self.last_bid = tick.bid
        self.high_ask = max(self.high_ask, tick.ask)
        self.low_ask = min(self.low_ask, tick.ask)
        self.last_ask = tick.ask
        mid = tick.mid
        self.high_mid = max(self.high_mid, mid)
        self.low_mid = min(self.low_mid, mid)
        self.last_mid = mid
        self.tick_count += 1

    def clone(self):
        return replace(self)

    def candle(self, state: CandleState) -> Candle:
        return Candle(
            symbol=self.symbol,
            timeframe=self.timeframe,
            boundary_profile=self.profile,
            time_open_utc=self.start,
            time_close_utc=self.end,
            state=state,
            bid_open=self.first_bid,
            bid_high=self.high_bid,
            bid_low=self.low_bid,
            bid_close=self.last_bid,
            ask_open=self.first_ask,
            ask_high=self.high_ask,
            ask_low=self.low_ask,
            ask_close=self.last_ask,
            mid_open=self.first_mid,
            mid_high=self.high_mid,
            mid_low=self.low_mid,
            mid_close=self.last_mid,
            tick_count=self.tick_count,
            quote_change_count=self.quote_change_count,
        )


@dataclass
class _Closed:
    accumulator: _Accumulator
    state: CandleState


@dataclass(frozen=True)
class CandleUpdate:
    timeframe: str
    candle: Candle
    kind: str


class CandleEngine:
    def __init__(self, timeframes: Iterable[str], profile: BoundaryProfile, *, grace_seconds: float = 2.0, source_offset_minutes: int = 0):
        self.timeframes = tuple(timeframes)
        self.profile = profile
        self.grace_seconds = float(grace_seconds)
        self.source_offset_minutes = int(source_offset_minutes)
        self._active: dict[str, _Accumulator] = {}
        self._closed: dict[str, list[_Closed]] = {tf: [] for tf in self.timeframes}
        self.revisions: list[CandleRevision] = []
        self._clock: datetime | None = None

    def _bounds(self, ts: datetime, tf: str):
        return bucket_bounds(ts, tf, self.profile, source_offset_minutes=self.source_offset_minutes)

    def _advance_for_tf(self, tf: str, now: datetime):
        active = self._active.get(tf)
        if active is not None and now >= active.end:
            self._closed[tf].append(_Closed(active, CandleState.PROVISIONALLY_CLOSED))
            del self._active[tf]
        if self._closed[tf]:
            last = self._closed[tf][-1]
            if last.state == CandleState.PROVISIONALLY_CLOSED and now >= last.accumulator.end + timedelta(seconds=self.grace_seconds):
                last.state = CandleState.FINAL

    def advance_clock(self, now: datetime):
        if now.tzinfo is None:
            raise ValueError('clock must be timezone-aware')
        self._clock = now.astimezone(timezone.utc)
        for tf in self.timeframes:
            self._advance_for_tf(tf, self._clock)

    def on_tick(self, tick: NormalizedTick) -> list[CandleUpdate]:
        received = tick.received_timestamp_utc.astimezone(timezone.utc)
        if self._clock is None or received > self._clock:
            self.advance_clock(received)
        updates: list[CandleUpdate] = []
        for tf in self.timeframes:
            start, end = self._bounds(tick.source_timestamp_utc, tf)
            active = self._active.get(tf)
            if active is not None and active.start == start:
                active.apply(tick)
                updates.append(CandleUpdate(tf, active.candle(CandleState.LIVE), 'UPDATE'))
                continue
            if self._closed[tf] and self._closed[tf][-1].accumulator.start == start:
                closed = self._closed[tf][-1]
                if closed.state == CandleState.PROVISIONALLY_CLOSED and received <= closed.accumulator.end + timedelta(seconds=self.grace_seconds):
                    closed.accumulator.apply(tick)
                    updates.append(CandleUpdate(tf, closed.accumulator.candle(closed.state), 'LATE_UPDATE'))
                continue
            if active is not None and start > active.start:
                self._advance_for_tf(tf, max(received, active.end))
            if tf not in self._active:
                self._active[tf] = _Accumulator.from_tick(tick, tf, self.profile, start, end)
                updates.append(CandleUpdate(tf, self._active[tf].candle(CandleState.LIVE), 'OPEN'))
        return updates

    def current(self, timeframe: str) -> Candle | None:
        acc = self._active.get(timeframe)
        return None if acc is None else acc.candle(CandleState.LIVE)

    def previous(self, timeframe: str) -> Candle | None:
        if not self._closed[timeframe]:
            return None
        closed = self._closed[timeframe][-1]
        return closed.accumulator.candle(closed.state)

    def finalized(self, timeframe: str) -> list[Candle]:
        return [item.accumulator.candle(item.state) for item in self._closed[timeframe] if item.state in {CandleState.FINAL, CandleState.CORRECTED, CandleState.RECOVERED}]

    def all_closed(self, timeframe: str) -> list[Candle]:
        return [item.accumulator.candle(item.state) for item in self._closed[timeframe]]

    def apply_authorized_correction(self, tick: NormalizedTick, *, reason: str) -> CandleRevision:
        corrected_at = tick.received_timestamp_utc.astimezone(timezone.utc)
        for tf in self.timeframes:
            start, _ = self._bounds(tick.source_timestamp_utc, tf)
            for item in reversed(self._closed[tf]):
                if item.accumulator.start == start:
                    old = item.accumulator.candle(item.state)
                    clone = item.accumulator.clone()
                    clone.apply(tick)
                    item.accumulator = clone
                    item.state = CandleState.CORRECTED
                    new = clone.candle(CandleState.CORRECTED)
                    rev = CandleRevision(f'{tick.symbol}|{tf}|{start.isoformat()}', corrected_at, reason, old, new)
                    self.revisions.append(rev)
                    return rev
        raise KeyError('no finalized candle matches correction tick')
