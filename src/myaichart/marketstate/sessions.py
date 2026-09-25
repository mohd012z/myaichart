from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_ZURICH = ZoneInfo('Europe/Zurich')
_DUKASCOPY_METALS = {'XAUUSD', 'XAGUSD'}


def dukascopy_reference_state(symbol: str, hour_utc: datetime) -> str | None:
    """Return Dukascopy reference state for an hourly XAU/XAG bucket.

    Dukascopy documents a weekly close/open and a one-hour metals trading
    break. During European summer time those boundaries are at 21:00 GMT;
    during winter time they move to 22:00 GMT. Observed ticks still take
    precedence in the market-state classifier.
    """
    if hour_utc.tzinfo is None:
        raise ValueError('hour_utc must be timezone-aware')
    if symbol.upper() not in _DUKASCOPY_METALS:
        return None

    hour = hour_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    zurich = hour.astimezone(_ZURICH)
    is_summer = bool(zurich.dst() and zurich.dst().total_seconds())
    boundary_hour_utc = 21 if is_summer else 22
    weekday = hour.weekday()

    # Weekly closure takes precedence at the Friday boundary. On Sunday the
    # market reopens at the boundary, but XAU/XAG immediately enter their
    # documented one-hour daily break before the first active hour.
    if (
        (weekday == 4 and hour.hour >= boundary_hour_utc)
        or weekday == 5
        or (weekday == 6 and hour.hour < boundary_hour_utc)
    ):
        return 'WEEKEND'

    if hour.hour == boundary_hour_utc:
        return 'SCHEDULED_BREAK'
    return None
