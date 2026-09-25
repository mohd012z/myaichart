from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

_ZURICH = ZoneInfo('Europe/Zurich')
_DUKASCOPY_METALS = {'XAUUSD', 'XAGUSD'}


def dukascopy_reference_state(symbol: str, hour_utc: datetime) -> str | None:
    """Return the documented Dukascopy reference state for an hourly bucket.

    Dukascopy documents a one-hour XAU/USD and XAG/USD trading break at
    21:00-22:00 GMT during European summer time and 22:00-23:00 GMT during
    winter time. This is reference context only; observed ticks still take
    precedence elsewhere in the market-state classifier.
    """
    if hour_utc.tzinfo is None:
        raise ValueError('hour_utc must be timezone-aware')
    if symbol.upper() not in _DUKASCOPY_METALS:
        return None

    hour = hour_utc.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    zurich = hour.astimezone(_ZURICH)
    is_summer = bool(zurich.dst() and zurich.dst().total_seconds())
    break_hour_utc = 21 if is_summer else 22
    if hour.hour == break_hour_utc:
        return 'SCHEDULED_BREAK'
    return None
