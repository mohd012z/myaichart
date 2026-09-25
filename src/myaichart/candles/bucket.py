from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from myaichart.models import BoundaryProfile

MYT = ZoneInfo('Asia/Kuala_Lumpur')
FIXED_MINUTES = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240}


def bucket_bounds(ts_utc: datetime, timeframe: str, profile: BoundaryProfile, *, source_offset_minutes: int = 0):
    if ts_utc.tzinfo is None:
        raise ValueError('timestamp must be timezone-aware')
    ts_utc = ts_utc.astimezone(timezone.utc)
    if timeframe in FIXED_MINUTES:
        size = FIXED_MINUTES[timeframe] * 60
        epoch = int(ts_utc.timestamp())
        start_epoch = epoch - (epoch % size)
        start = datetime.fromtimestamp(start_epoch, timezone.utc)
        return start, start + timedelta(seconds=size)
    tz = MYT if profile == BoundaryProfile.MYT_CALENDAR else timezone(timedelta(minutes=source_offset_minutes))
    local = ts_utc.astimezone(tz)
    if timeframe == 'D1':
        start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
    elif timeframe == 'W1':
        start_local = (local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=7)
    elif timeframe == 'MN1':
        start_local = local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start_local.month == 12:
            end_local = start_local.replace(year=start_local.year + 1, month=1)
        else:
            end_local = start_local.replace(month=start_local.month + 1)
    else:
        raise ValueError(f'unsupported timeframe {timeframe}')
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)
