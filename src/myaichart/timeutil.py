from datetime import datetime, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc
MYT = ZoneInfo('Asia/Kuala_Lumpur')


def to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError('naive datetime not allowed')
    return value.astimezone(UTC)


def to_myt(value: datetime) -> datetime:
    return to_utc(value).astimezone(MYT)
