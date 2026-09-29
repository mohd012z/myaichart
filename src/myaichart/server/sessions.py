"""Server-authoritative session zones (Tokyo / US first candle).

Per the cluster invariant, the session zone is computed from canonical
candles on the SERVER, not in the browser — the chart renders it read-only.
The *authoritative* first-completed-candle lock lives in helix's
session-engine; this is the display projection: the first M1 candle at/after
a session open, reported as a high/low zone. DST-safe via zoneinfo.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

from myaichart.models import Candle

_TOKYO_TZ = ZoneInfo("Asia/Tokyo")
_US_TZ = ZoneInfo("America/New_York")
_TOKYO_OPEN = time(9, 0)
_US_OPEN = time(9, 30)


@dataclass(frozen=True)
class SessionZone:
    name: str
    exchange_tz: str
    open_utc: datetime
    high: float
    low: float
    first_candle_utc: datetime
    source: str = "FIRST_CANDLE"


def _latest_open_utc(now_utc: datetime, local_open: time, tz: ZoneInfo) -> datetime:
    """Most recent session-open instant (UTC) at or before now_utc.

    Walks back through the session's *local* calendar (today, yesterday,
    day-before). A session's local date can be ahead of the UTC date — Tokyo
    (+9) at 16:00Z is already 01:00 local the next day — so using the UTC
    date (or walking offsets in the wrong direction) can pick an open that
    hasn't happened yet. We therefore enumerate local-day candidates and keep
    the latest one that is at or before ``now_utc``.
    """
    local_now = now_utc.astimezone(tz)
    best = None
    for day_offset in (0, 1, 2):  # today, yesterday, day-before — in local days
        candidate_local = (local_now - timedelta(days=day_offset)).replace(
            hour=local_open.hour, minute=local_open.minute,
            second=0, microsecond=0)
        candidate_utc = candidate_local.astimezone(timezone.utc)
        if candidate_utc <= now_utc and (best is None or candidate_utc > best):
            best = candidate_utc
    if best is None:
        # Defensively unreachable (an open must have happened within the last
        # 2 local days); fall back to the oldest candidate.
        best = (local_now - timedelta(days=2)).replace(
            hour=local_open.hour, minute=local_open.minute,
            second=0, microsecond=0).astimezone(timezone.utc)
    return best


def first_candle_zone(candles: list[Candle], open_utc: datetime) -> SessionZone | None:
    """First candle at/after open_utc (its high/low is the session zone)."""
    for c in candles:
        if c.time_open_utc >= open_utc:
            return SessionZone(
                name=c.timeframe,
                exchange_tz="",
                open_utc=open_utc,
                high=c.mid_high,
                low=c.mid_low,
                first_candle_utc=c.time_open_utc,
            )
    return None


def session_zones(m1_candles: list[Candle], now_utc: datetime) -> list[SessionZone]:
    """Tokyo + US first-candle zones for the most recent session each."""
    now = now_utc.astimezone(timezone.utc)
    out = []
    for name, tz, open_local in (("TOKYO", _TOKYO_TZ, _TOKYO_OPEN), ("US", _US_TZ, _US_OPEN)):
        open_utc = _latest_open_utc(now, open_local, tz)
        z = first_candle_zone(m1_candles, open_utc)
        if z is not None:
            out.append(SessionZone(name=name, exchange_tz=tz.key, open_utc=open_utc,
                                   high=z.high, low=z.low, first_candle_utc=z.first_candle_utc))
    return out
