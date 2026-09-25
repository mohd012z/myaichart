from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from myaichart.models import BoundaryProfile
from myaichart.timeutil import to_myt
from myaichart.candles.bucket import bucket_bounds


def test_utc_to_myt_is_plus_eight_without_dst():
    dt = datetime(2026, 9, 25, 8, 0, tzinfo=timezone.utc)
    assert to_myt(dt).isoformat() == '2026-09-25T16:00:00+08:00'


def test_m5_bucket_uses_canonical_utc_boundary():
    dt = datetime(2026, 9, 25, 7, 42, 13, tzinfo=timezone.utc)
    start, end = bucket_bounds(dt, 'M5', BoundaryProfile.MYT_CALENDAR)
    assert start.isoformat() == '2026-09-25T07:40:00+00:00'
    assert end.isoformat() == '2026-09-25T07:45:00+00:00'


def test_myt_daily_bucket_starts_at_myt_midnight():
    dt = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
    start, end = bucket_bounds(dt, 'D1', BoundaryProfile.MYT_CALENDAR)
    assert start.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).hour == 0
    assert end.astimezone(ZoneInfo('Asia/Kuala_Lumpur')).hour == 0


def test_source_session_daily_uses_supplied_offset():
    dt = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)
    start, _ = bucket_bounds(dt, 'D1', BoundaryProfile.SOURCE_SESSION, source_offset_minutes=120)
    assert start.isoformat() == '2026-09-24T22:00:00+00:00'


def test_cli_six_month_range_uses_calendar_months_not_180_days():
    from argparse import Namespace
    from myaichart.cli import _range
    args=Namespace(from_time=None,to_time='2026-09-25 18:00',months=6)
    start,end=_range(args)
    assert end.isoformat() == '2026-09-25T10:00:00+00:00'
    assert start.isoformat() == '2026-03-25T10:00:00+00:00'


def test_cli_explicit_aware_timestamp_preserves_its_offset():
    from argparse import Namespace
    from myaichart.cli import _range
    args=Namespace(from_time='2026-09-25T10:00:00+00:00',to_time='2026-09-25T11:00:00+00:00',months=6)
    start,end=_range(args)
    assert start.isoformat() == '2026-09-25T10:00:00+00:00'
    assert end.isoformat() == '2026-09-25T11:00:00+00:00'
